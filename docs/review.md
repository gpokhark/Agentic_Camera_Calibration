The heuristic baseline we are currently using is a rule-based recovery controller in [heuristic_controller.py](d:/github/Agentic_Camera_Calibration/src/agentic_camera_calibration/controllers/heuristic_controller.py:1), based on the heuristic design described in [architecture.md](d:/github/Agentic_Camera_Calibration/docs/architecture.md:980).

What it actually does right now:
- If saturation is high, it rejects bad frames using a saturation threshold.
- If blur is high, it rejects bad frames using a blur threshold.
- If the run looks low-light, it applies `clahe`.
- If glare is present, it applies `contrast_normalization`.
- If corner count is low and reserved frames exist, it requests more frames.
- If coverage is low and reserved frames exist, it requests edge-coverage frames.
- If reprojection error is high, it retries with a filtered subset.
- If pose is out of range but image quality is otherwise okay, it relaxes the nominal prior.
- If the same failure pattern repeats, or no useful deterministic action remains, it declares unrecoverable.

So the heuristic is not “do one obvious thing and stop.” It is:
- threshold-based
- multi-action
- retry-aware
- allowed to terminate
- sharing the same action space as the agent

That last point matters a lot: the heuristic and the agent both operate on the same structured state and the same allowed recovery actions. That is good experimental design.

The architecture doc originally proposed an even richer heuristic table in [architecture.md](d:/github/Agentic_Camera_Calibration/docs/architecture.md:996), including combined rules like:
- overexposure + low corners
- low light + low corners
- partial visibility + low coverage
- repeated-failure stopping logic

My honest read is:
- the current heuristic is credible
- but it is not yet as strong as it could be
- and yes, a reviewer could reasonably challenge whether it is “good enough”

If a reviewer says the heuristic is not strong enough, that is a serious concern, because the whole agent-vs-heuristic claim depends on the heuristic being a fair baseline. The best response is not to argue abstractly; it is to make the baseline harder to beat and document that clearly.

The strongest ways to defend the paper are:
- State that the heuristic is a hand-engineered deterministic baseline using the same observations, same retry budget, same action space, and same executor as the agent.
- Show the full heuristic rule table explicitly in the paper, not just prose.
- Tune heuristic thresholds on a small development split, then freeze them before final evaluation.
- Include combined-condition rules, not just single-threshold rules.
- Report where heuristic already works well, so you are not making it look artificially weak.
- Show that the agent’s gains appear mainly on mixed or interacting failures, not on easy single-cause cases.

If you want the reviewer-proof version of this project, I would recommend strengthening the heuristic in code before treating the comparison as paper-ready. Specifically:
- implement the missing combination rules from the architecture doc
- document all thresholds and how they were chosen
- maybe add a “best heuristic tuned on validation runs” version
- keep the same action budget and same retry budget as the agent

A reviewer is much less likely to object if they see:
- a nontrivial heuristic
- transparent tuning procedure
- same information available to both systems
- agent gains only where contextual reasoning should matter

So the short answer is:
- the current heuristic is a deterministic threshold-and-rule controller with multiple recovery actions
- it is a decent baseline
- but if the paper’s main claim is “agent beats heuristic,” then I would strengthen it further before final submission

If you want, I can do the next practical step and upgrade the heuristic controller to match the fuller rule table in `architecture.md`, so your baseline is much harder to criticize.