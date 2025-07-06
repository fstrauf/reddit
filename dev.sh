#!/bin/bash

# Increase the file descriptor limit for this session
ulimit -n 10240

# Run the development server
pnpm run dev