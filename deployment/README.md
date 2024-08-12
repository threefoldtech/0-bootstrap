# Docker Build for 0-bootstrap

Build the image using the Dockerfile. When it's ready, here are some point you need to run the bootstrap service:
- Override `config.py` from host with a mount to: `/bootstrap/config.py`
- Provide a kernel directory
  - Use a **per-network** directory, which is a directory with 4 symlinks (prod, net, dev, qa).
