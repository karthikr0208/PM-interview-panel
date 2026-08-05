"""Golden cases for the Interviewer agent.

Run with `make golden AGENT=interviewer`, or directly with
`pytest tests/golden/interviewer -v`. See
`docs/specs/agents/AGENT-INTERVIEWER-SPEC.md` §5 for the case table this
package implements -- that spec is the authority; this package is not.

Written BLIND, before `app.agents.interviewer` exists (story 3.1, ahead of
story 3.2), so the prompt can never be tuned against this suite.
"""
