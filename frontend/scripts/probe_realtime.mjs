#!/usr/bin/env node
// Disposable probe, story 1.6b. Proves Supabase Realtime respects RLS for a
// real subscriber under a real second identity, before any UI is built on
// top of it (see PHASE-1-SPEC.md 1.6, "Live updates arrive via Supabase
// Realtime on agent_events"). Not part of the shipped app -- safe to delete
// once the finding is recorded in DEV-STATE.
//
// Reads frontend/.env (anon key, the browser's own credentials) and
// backend/.env (SUPABASE_SERVICE_ROLE_KEY -- what the backend will use to
// write agent_events in story 1.4) directly, with no dotenv dependency.
import { createClient } from '@supabase/supabase-js'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, '..', '..')

function loadEnv(relPath) {
  const text = readFileSync(path.join(repoRoot, relPath), 'utf-8')
  const out = {}
  for (const line of text.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq === -1) continue
    const key = trimmed.slice(0, eq).trim()
    let value = trimmed.slice(eq + 1).trim()
    value = value.replace(/^["']|["']$/g, '')
    out[key] = value
  }
  return out
}

const frontendEnv = loadEnv('frontend/.env')
const backendEnv = loadEnv('backend/.env')

const SUPABASE_URL = frontendEnv.VITE_SUPABASE_URL
const SUPABASE_ANON_KEY = frontendEnv.VITE_SUPABASE_ANON_KEY
const SERVICE_ROLE_KEY = backendEnv.SUPABASE_SERVICE_ROLE_KEY

if (!SUPABASE_URL || !SUPABASE_ANON_KEY || !SERVICE_ROLE_KEY) {
  console.error(
    'Missing one of VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY (frontend/.env) or ' +
      'SUPABASE_SERVICE_ROLE_KEY (backend/.env).',
  )
  process.exit(1)
}

// persistSession: false -- this is Node, there is no localStorage, and each
// of A/B/service needs its OWN in-memory session rather than sharing one via
// a shared storage backend.
const noPersist = {
  auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
}

const clientA = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, noPersist)
const clientB = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, noPersist)
const service = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, noPersist)

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function main() {
  const cleanup = { sessionIds: [], userIds: [] }
  let channel = null
  let serviceChannel = null
  let overallPass = false

  try {
    console.log('=== 1. Minting two anonymous identities (A, B) ===')
    const { data: authA, error: authAErr } = await clientA.auth.signInAnonymously()
    if (authAErr) throw new Error(`signInAnonymously A failed: ${authAErr.message}`)
    const { data: authB, error: authBErr } = await clientB.auth.signInAnonymously()
    if (authBErr) throw new Error(`signInAnonymously B failed: ${authBErr.message}`)
    cleanup.userIds.push(authA.user.id, authB.user.id)
    console.log(`  A uid=${authA.user.id}`)
    console.log(`  B uid=${authB.user.id}`)

    console.log('=== 2. Creating one sessions row per identity (INSERT policy: user_id = auth.uid()) ===')
    const { data: sessA, error: sessAErr } = await clientA
      .from('sessions')
      .insert({ user_id: authA.user.id })
      .select()
      .single()
    if (sessAErr) throw new Error(`A session insert failed: ${sessAErr.message}`)
    const { data: sessB, error: sessBErr } = await clientB
      .from('sessions')
      .insert({ user_id: authB.user.id })
      .select()
      .single()
    if (sessBErr) throw new Error(`B session insert failed: ${sessBErr.message}`)
    cleanup.sessionIds.push(sessA.id, sessB.id)
    console.log(`  A session=${sessA.id}`)
    console.log(`  B session=${sessB.id}`)

    console.log('=== 3. Subscribing as A to postgres_changes INSERT on agent_events ===')
    // The socket connection does not inherit the PostgREST client's JWT for
    // free -- Realtime evaluates RLS against whatever token the SOCKET was
    // authorized with, so it has to be handed the token explicitly.
    await clientA.realtime.setAuth(authA.session.access_token)

    const received = []
    channel = clientA.channel('probe-agent-events').on(
      'postgres_changes',
      { event: 'INSERT', schema: 'public', table: 'agent_events' },
      (payload) => {
        received.push(payload.new)
      },
    )

    await new Promise((resolve, reject) => {
      const timeout = setTimeout(
        () => reject(new Error('Subscription never reached SUBSCRIBED within 15s')),
        15000,
      )
      channel.subscribe((status, err) => {
        console.log(`  [A channel status] ${status}${err ? ' ' + err.message : ''}`)
        if (status === 'SUBSCRIBED') {
          clearTimeout(timeout)
          resolve()
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
          clearTimeout(timeout)
          reject(new Error(`Subscription failed with status ${status}: ${err?.message ?? ''}`))
        }
      })
    })
    console.log('  subscribed (status=SUBSCRIBED)')

    console.log('=== 3b. CONTROL: also subscribing with the service role (bypasses RLS) ===')
    // If this control receives nothing either, the finding is "Realtime
    // delivery is broken/not configured" rather than "RLS specifically
    // denies A" -- the two look identical from A's channel alone.
    const receivedByService = []
    serviceChannel = service.channel('probe-agent-events-service').on(
      'postgres_changes',
      { event: 'INSERT', schema: 'public', table: 'agent_events' },
      (payload) => {
        receivedByService.push(payload.new)
      },
    )
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(
        () => reject(new Error('Service control subscription never reached SUBSCRIBED within 15s')),
        15000,
      )
      serviceChannel.subscribe((status, err) => {
        console.log(`  [service channel status] ${status}${err ? ' ' + err.message : ''}`)
        if (status === 'SUBSCRIBED') {
          clearTimeout(timeout)
          resolve()
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
          clearTimeout(timeout)
          reject(new Error(`Service control subscription failed with status ${status}: ${err?.message ?? ''}`))
        }
      })
    })
    console.log('  service control subscribed (status=SUBSCRIBED)')

    // 🔴 DEFAULT 2000 SINCE 2026-08-11, was 0. `SUBSCRIBED` is not the same
    // event as "the RLS-scoped filter is live server-side", and inserting in
    // the gap between them loses the row for the `authenticated` subscriber
    // while the service-role control still receives it -- which is exactly the
    // shape this probe reported, repeatedly, as a false FAIL.
    //
    // Measured, same session, same machine, no other change:
    //     default 0ms     2 PASS / 4 runs
    //     settle 2000ms   3 PASS / 3 runs
    //
    // The DENIAL half never failed in any run, so nothing here weakens what
    // the probe proves: it removes a startup race in the PROBE, not a check.
    // The product does not have this race -- `lib/agentEvents.ts` documents it,
    // and the columns subscribe when a session id first exists, minutes before
    // any row is written.
    const settleMs = Number(process.env.PROBE_SETTLE_MS || 2000)
    if (settleMs > 0) {
      console.log(`=== 3c. EXPERIMENT: settling ${settleMs}ms before the first insert ===`)
      await sleep(settleMs)
    }

    console.log('=== 4. Service role inserts one agent_events row into EACH session ===')
    // This is what story 1.4's backend will do -- the service key bypasses
    // RLS entirely on the write side, which is correct; what this probe
    // checks is the READ side, per-subscriber, under RLS.
    const { data: eventA, error: eventAErr } = await service
      .from('agent_events')
      .insert({
        session_id: sessA.id,
        agent: 'resume_analyst',
        status: 'done',
        summary: 'probe event for A',
      })
      .select()
      .single()
    if (eventAErr) throw new Error(`insert event A failed: ${eventAErr.message}`)
    const { data: eventB, error: eventBErr } = await service
      .from('agent_events')
      .insert({
        session_id: sessB.id,
        agent: 'resume_analyst',
        status: 'done',
        summary: 'probe event for B',
      })
      .select()
      .single()
    if (eventBErr) throw new Error(`insert event B failed: ${eventBErr.message}`)
    console.log(`  event A id=${eventA.id} (session ${sessA.id})`)
    console.log(`  event B id=${eventB.id} (session ${sessB.id})`)

    console.log('=== 5. Waiting up to 8s for realtime delivery ===')
    await sleep(8000)

    const receivedOwnA = received.some((row) => row.id === eventA.id)
    const receivedBsRow = received.some((row) => row.id === eventB.id)
    const serviceReceivedA = receivedByService.some((row) => row.id === eventA.id)
    const serviceReceivedB = receivedByService.some((row) => row.id === eventB.id)

    console.log('')
    console.log('=== RESULT — received vs expected, both directions ===')
    console.log('  check                            expected  observed  verdict')
    console.log(
      `  A receives its OWN row (A/own)   1         ${receivedOwnA ? 1 : 0}         ` +
        `${receivedOwnA ? 'PASS  <- positive control' : 'FAIL'}`,
    )
    console.log(
      `  A receives B's row     (A/Bs)    0         ${receivedBsRow ? 1 : 0}         ` +
        `${!receivedBsRow ? 'PASS  <- denial' : 'FAIL'}`,
    )
    console.log('')
    console.log(
      '  raw rows delivered to A:',
      JSON.stringify(received.map((r) => ({ id: r.id, session_id: r.session_id }))),
    )
    console.log('')
    console.log('=== CONTROL — service role (bypasses RLS), same two INSERTs ===')
    console.log(`  service receives A's row   observed=${serviceReceivedA ? 1 : 0}`)
    console.log(`  service receives B's row   observed=${serviceReceivedB ? 1 : 0}`)
    console.log(
      '  raw rows delivered to service:',
      JSON.stringify(receivedByService.map((r) => ({ id: r.id, session_id: r.session_id }))),
    )

    if (!receivedOwnA) {
      console.log('')
      if (serviceReceivedA && serviceReceivedB) {
        console.log(
          'VACUITY WARNING, NARROWED BY THE CONTROL: the service-role subscriber received both ' +
            'rows fine, so Realtime delivery itself works and the publication is correctly ' +
            "configured. A's own row was still not delivered to A, which points specifically at " +
            'RLS/auth on the authenticated-role subscription, not at Realtime being broken.',
        )
      } else {
        console.log(
          'VACUITY WARNING: A received NOTHING, including its own row, AND the service-role ' +
            'control also failed to receive one or both rows. The denial result above is ' +
            'therefore NOT evidence RLS is scoping correctly -- Realtime delivery itself is not ' +
            'working (publication, replication, or connectivity), independent of RLS.',
        )
      }
    }

    overallPass = receivedOwnA && !receivedBsRow
    console.log('')
    console.log(
      overallPass
        ? 'OVERALL: PASS -- Realtime respects RLS per subscriber (own row delivered, other session denied).'
        : 'OVERALL: FAIL',
    )
  } finally {
    if (channel) {
      await clientA.removeChannel(channel)
    }
    if (serviceChannel) {
      await service.removeChannel(serviceChannel)
    }
    console.log('')
    console.log('=== 6. Cleanup ===')
    for (const id of cleanup.sessionIds) {
      // agent_events rows cascade-delete with their session (`references
      // sessions on delete cascade`, migrations/0001_initial_schema.sql) --
      // no separate delete needed for them.
      const { error } = await service.from('sessions').delete().eq('id', id)
      console.log(`  delete session ${id}: ${error ? 'FAILED ' + error.message : 'ok'}`)
    }
    for (const id of cleanup.userIds) {
      const { error } = await service.auth.admin.deleteUser(id)
      console.log(`  delete auth user ${id}: ${error ? 'FAILED ' + error.message : 'ok'}`)
    }
  }

  process.exitCode = overallPass ? 0 : 1
}

main().catch((err) => {
  console.error('PROBE FAILED:', err)
  process.exitCode = 1
})
