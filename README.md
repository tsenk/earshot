<h1 align="center">Earshot</h1>
Earshot: Fast real-time speech translation (60+ base languages and more with model switch) for group voice calls. With diarization via individual speaker pre-enrollment (15s) and long-running discussion context. Highly customizable & optimizable 100% local inference

# Demos `TODO`
# Hardware Requirements `TODO`
# Setup `WIP`
# Usage `WIP`
# Limitations in real-world use `WIP`
# Optimization `TODO`
# Fine-tuning `TODO`
# Details `TODO`
<h1 align="center">Contribute</h1>

- See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, details and coding guidelines. (`TODO`)
- Since the project is in its infancy, well-documented testing in real use (excluding sensitive discussions) would be invaluable. Ideally, submissions should include original audio recordings for comparison.
- Bug-hunting and PRs will also be highly appreciated.

<h1 align="center">WIP</h1>

- [ ] Full, working & tested TUI
- [ ] Pick default translation model to ship with
- [ ] Fine-tuning selection workflow from triple output choice
- [ ] Dynamic enrollment window replacing fixed (15s) with user-based snipping/patching over parts of enrollment audio
- [ ] Testing in use in different scenarios
- [ ] Certain README.md sections

<h1 align="center">Future</h1>

- [ ] Fill in README.md sections
- [ ] Default config fine-tuning (thresholds)
- [ ] Fine-tuning (bundled on default) translation model's settings 
- [ ] GUI ahead
  - Decision between Overlay/GUI
- [ ] Rolling discussion context window AHEAD
  - Decision between fully via `generate prompt context footer -> additional model -> addition in translation model's prompt` or `pre-parsing -> additonal model -> translation model's prompt`
