# sizer

Automatically size all design parameters in a circuit to meet design specifications

## Quickstart

Note: Windows is currently not supported because the dependency [PySpice](https://github.com/FabriceSalvaire/PySpice) has [an issue](https://github.com/FabriceSalvaire/PySpice/issues/23) with raw data parsing. If you *really* have to try on Windows, you can follow [my comment here](https://github.com/FabriceSalvaire/PySpice/issues/23#issuecomment-452176011). However, it is not a perfect solution because it can't tell if a `\r\n` comes as a part of bytes that represent a number or as just a line break.

1. clone this repo

    ```sh
    git clone https://github.com/aiifabbf/sizer.git
    ```

1. set up a virtual environment (recommended)

    ```sh
    cd ./sizer
    python3 -m venv env
    . env/bin/activate
    ```

    If you have installed numpy, scipy as system-level site packages, you can apply the `--system-site-packages` to avoid duplicate installation.
    ```sh
    cd ./sizer
    python3 -m venv env --system-site-packages
    . env/bin/activate
    ```

1. install dependencies

    ```sh
    pip install -r requirements.txt
    ```

1. ready to go! Check out demo!

    ```sh
    python3 demos/two-stage-amplifier/main.py
    ```

## Demo: a simple-Miller compensated two-stage amplifier

![structure of simple miller compensated two-stage amplifier](./demos/two-stage-amplifier/schematic.png)

Design specifications chosen:
- DC gain >= 1000x
- phase margin >= 60 deg
- bandwidth >= 5 kHz

Variable parameters:
- 12 sizes(width and length) for all MOSFETs(current mirror not shown)
- 1 compensation capacitance

Fixed parameters:
- supply voltage = 3.3 V
- load capacitance = 4 pF
- bias current = 10 uA
- input bias voltage = 1.65 V

[![automatically designed two stage amplifier's frequency response](./demos/two-stage-amplifier/two-stage-amplifier-frequency-response.png)](./demos/two-stage-amplifier/main.py)

After 1 min (on my i5 3rd generation CPU), all 3 specifications are met:
- DC gain ~= 1387x
- phase margin ~= 79.66 deg
- bandwidth ~= 5.298 kHz

Challenge: can you come up with a choice of all MOSFETs' sizes and the compensation capacitance to meet all the design specs **within 1 min?**

## Why

I enjoy playing with circuit topology, but I am tired of calculating sizes to meet design specifications.

A typical workflow for analog circuit design might be
1. you have a circuit topology
1. list small-signal equations and inequalities according to design specs
1. try solving these equations and inequalities. Most of your time is spent on some ~~nonsense~~ magical assumption that approximates the system to make your life easier ~~hopefully~~.
1. send these manually-calculated parameters to a circuit simulator and check if they work:
    - they work -> hooray
    - they don't work -> go back to step 3
    - you run out of patience and quit the job

A typical workflow with sizer might be
1. you have a topology
1. choose variable parameters and their bounds
1. define a loss function
1. give it to `sizer.optimizers.Optimizer`
1. wait ~~a year~~ until it returns you an optimal set of parameters

It is basically handing the tedious trial-and-error to a program instead of doing everything on our own.

A fundamental idea behind this is that I believe simulators are our friends and the most trustworthy tool throughout the whole design procedure. Although they are *not* the perfect reflection of how our design would work in real life, they are still the closest to it.

I was taught so many times with assertions like
> Don't do simulation until you know what you would expect from your design.

I just don't know...this three-stage amplifier is too complex for my mind.

> Simulators are inaccurate.

but manual calculation is also full of approximation (otherwise you are stuck at workflow 1 step 3), much much more inaccurate than simulators. If you believe in your hand calc, why in the world should you not trust simulators?