# Commands
## S0
```shell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S0_nominal\run_10 --scenario S0_nominal --run-id run_10 --primary-count 12 --reserved-count 6 --notes "recaptured nominal run 10 with 2 tripod stands"
```
## S1
```shell
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S1_overexposed\run_10 --scenario S1_overexposed --run-id run_10 --primary-count 12 --reserved-count 6 --notes "Run 10 overexposed capture session with glare/bright highlights"
```

## S2

```bash
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S2_low_light\run_10 --scenario S2_low_light --run-id run_10 --primary-count 12 --reserved-count 6 --notes "Run 10 low-light capture session"
```

## S3

```bash
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S3_pose_deviation\run_10 --scenario S3_pose_deviation --run-id run_10 --primary-count 12 --reserved-count 6 --notes "Run 10 pose deviation -roll anti-clocwise 4-5 degrees capture session"

```

## S4 Height Variation
```bash
.venv\Scripts\accal capture-guided --camera-index 0 --output-dir dataset\S4_height_variation\run_10 --scenario S4_height_variation --run-id run_10 --primary-count 12 --reserved-count 6 --notes "Run 10 height -50mm capture session"
```

## Reference Frames
```bash
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\S0_nominal\run_10\reference_frames --scenario S0_nominal --run-id run_10 --frame-count 3 --notes "fixed nominal reference frames"
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\S3_pose_deviation\run_10\reference_frames --scenario S3_pose_deviation --run-id run_10 --frame-count 3 --notes "fixed reference frames before pose-deviation run"
.venv\Scripts\accal capture-reference --camera-index 0 --output-dir dataset\S4_height_variation\run_10\reference_frames --scenario S4_height_variation --run-id run_10 --frame-count 3 --notes "fixed reference frames before height-variation run"
```
