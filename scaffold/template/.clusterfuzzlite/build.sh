#!/bin/bash -eu
# SPDX-FileCopyrightText: BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#
# ClusterFuzzLite / OSS-Fuzz build script for this repo's Atheris harnesses.
# Runs inside the base-builder-python image (see .clusterfuzzlite/Dockerfile),
# with $SRC/project as the working directory and $OUT as the fuzzer output dir.
# Generated VERBATIM by breachsafe-repo (no per-repo template vars needed).

# Install the package plus the fuzz extra so the harnesses can import the
# package under test and atheris>=3.1 at fuzz time.
pip3 install --no-cache-dir '.[fuzz]'

# Package each tests/fuzz/fuzz_*.py harness into a standalone libFuzzer target.
# compile_python_fuzzer is provided by the OSS-Fuzz base image; it bundles the
# harness and its dependencies with Atheris coverage instrumentation.
for harness in tests/fuzz/fuzz_*.py; do
  compile_python_fuzzer "$harness"
done
