# **Quick Start Guide to Initializing a New Clan Project**

This guide will lead you through initiating a new Clan project

## **Overview**

Dive into our structured guide tailored to meet your needs:

- [**Starting with a New Clan Project**](#starting-with-a-new-clan-project): Create a new Clan from scratch
- [**Migrating Existing Flake Configuration**](migrate.md#migrating-existing-nixos-configuration-flake): Transition your existing flake-based Nix configuration to Clan.

- [**Integrating Clan using Flake-Parts**](./migrate.md#integrating-clan-with-flakes-using-flake-parts)

---

## Starting with a New Clan Project

Create your own clan with these initial steps:

### Step 1: Add Clan CLI to Your Shell

Add the Clan CLI into your development workflow:

```shell
nix shell git+https://git.clan.lol/clan/clan-core
```

### Step 2: Initialize Your Project

Set the foundation of your Clan project by initializing it as follows

```shell
clan flakes create my-clan
```

This command creates the `flake.nix` and `.clan-flake` files for your project.

### Step 3: Verify the Project Structure

Ensure the creation of your project files with a quick directory listing

```shell
cd my-clan && ls -la
```

Look for `.clan-flake`, `flake.lock`, and `flake.nix` among your files to confirm successful setup.

### Next Steps

### Edit Flake.nix

Open the `flake.nix` file and set a unique `clanName` if you want you can also set an optional `clanIcon` or even a per `machineIcon`. These will be used by our future clan GUI.

### Remote into the target machine

**Right now clan assumes that you already have NixOS running on the target machine.**

If that is not the case you can use our [installer image](./install-iso.md) that automatically generates an endpoint reachable over TOR with a random ssh password.

On the remote execute:
1. Generate a hardware-config.nix 
    ```bash
    nixos-generate-config --root /etc/nixos --no-filesystems
    ```
2. Copy it over and put it into you `machines/jon/hardware-config.nix` folder
    ```bash
    scp -r root@<jon-ip>:/etc/nixos/hardware-config.nix ./machines/jon
    ```
3. Find the remote disk id by executing on the remote:
    ```bash
    lsblk --output NAME,PTUUID,FSTYPE,SIZE,MOUNTPOINT
    ```
4. Edit the following fields inside the `flake.nix`
    - `clan.networking.targetHost = pkgs.lib.mkDefault "root@<IP_ADDRESS>";`
    - `clan.diskLayouts.singleDiskExt4 = {
                  device = "/dev/disk/by-id/__CHANGE_ME__";
                };`

5. Generate secrets used by clan modules by executing
    ```bash
    clan facts generate
    ```

### **Next Steps**
Ready to expand? Explore how to install a new machine with the helpful documentation [here](./machines.md).
Ready to explore more?

- Learn how to add new machines [here](./machines.md).

---
