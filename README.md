The EC2 Spot hibernation agent.

This agent does several things:

1. Upon startup it checks for sufficient swap space to allow hibernate and fails
    if it's present but there's not enough of it.
2. If there's no swap space, it creates it and launches a background thread to
    touch all of its blocks to make sure that EBS volumes are pre-warmed.
3. It updates the offset of the swap file in the kernel using SNAPSHOT_SET_SWAP_AREA ioctl.
4. It daemonizes and starts a polling thread to listen for instance termination notifications.
