# SPDX-FileCopyrightText: BreachSAFE
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#
# ClusterFuzzLite build image for this repo's Atheris parser harnesses.
# Based on the OSS-Fuzz Python base builder, which ships Atheris, the coverage
# instrumentation, and the `compile_python_fuzzer` helper build.sh relies on.
# Generated VERBATIM by breachsafe-repo (no per-repo template vars needed: the
# checkout dir name is arbitrary and build.sh installs the local package).
FROM gcr.io/oss-fuzz-base/base-builder-python

# Place the checkout in the OSS-Fuzz source workspace and install the build
# script ClusterFuzzLite invokes from $SRC.
COPY . $SRC/project
COPY .clusterfuzzlite/build.sh $SRC/build.sh
WORKDIR $SRC/project
