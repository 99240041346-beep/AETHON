# Android command transport

The Android command client uses authenticated bearer transport and delegates received capabilities only through the bounded Android capability registry and action executor.

Foreground execution is declared as a non-exported `dataSync` service. Physical-device verification remains an explicit runtime gate.
