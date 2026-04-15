I checked `run_01` from both [S0_nominal](d:/github/Agentic_Camera_Calibration/dataset/S0_nominal/run_01) and [S2_low_light](d:/github/Agentic_Camera_Calibration/dataset/S2_low_light/run_01) using the repo’s own detector, quality analyzer, and calibration engine, and I also spot-checked a couple of frames visually.

My short verdict:
- `S0_nominal/run_01` is good enough to keep for analysis.
- `S2_low_light/run_01` is usable as a low-light disturbance run, but not “good quality” imagery in the clean-calibration sense.

For `S0_nominal/run_01`, the images look strong overall. All 18 frames were detected successfully, all 18 passed the current quality thresholds, and calibration succeeded with a low reprojection error around `0.19` on all 18 frames and `0.15` on the initial 12. Visually, frames like [frame_004.png](d:/github/Agentic_Camera_Calibration/dataset/S0_nominal/run_01/frame_004.png) and [frame_011.png](d:/github/Agentic_Camera_Calibration/dataset/S0_nominal/run_01/frame_011.png) are sharp and clearly readable. The only warnings came from the failure detector: `low_marker_coverage` and `pose_out_of_range`. I would not treat those as “bad images” here. The coverage score is a bit conservative in this implementation, and the pose warning is likely coming from the nominal-pose comparison rather than the images being poor. So for practical purposes: this run is good for analysis and worth keeping.

For `S2_low_light/run_01`, the story is more nuanced. Visually, [frame_001.png](d:/github/Agentic_Camera_Calibration/dataset/S2_low_light/run_01/frame_001.png) and [frame_011.png](d:/github/Agentic_Camera_Calibration/dataset/S2_low_light/run_01/frame_011.png) are clearly very dark, which is exactly what we want for the low-light scenario. Quantitatively, all 18 frames still produced successful ChArUco detections, and calibration still succeeded with low reprojection error around `0.20`. That means the run is not useless at all. But the quality analyzer rated `0/18` frames as usable because the mean brightness is only about `21` and blur is borderline at about `48`, which triggered `low_light` and `blur_or_low_detail`. So if your question is “are these good clean images for standard calibration?” then no. If your question is “are these good images for the `S2_low_light` disturbance experiment?” then yes, they are valid and actually pretty effective.

The main takeaway is:
- `S0_nominal/run_01`: keep it
- `S2_low_light/run_01`: keep it as low-light scenario data, but expect it to be flagged as degraded by the pipeline

One useful note for future collection: your `S2` run may be slightly too dark if you want a mix of recoverable and difficult low-light examples. Right now it is strongly low-light, which is okay, but future runs could be a little brighter so the scenario has more internal variation.

If you want, I can next analyze all runs in `S0_nominal` and `S2_low_light` and give you a ranked summary of which runs are strongest, weakest, and should be recaptured.