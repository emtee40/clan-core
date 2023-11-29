(import ../lib/test-base.nix) {
  name = "from-nixos";
  nodes = {
    installer = ./installer.nix;
    installed = {
      services.openssh.enable = true;
      virtualisation.memorySize = 1512;

      users.users.root.openssh.authorizedKeys.keyFiles = [ ./ssh-keys/ssh.pub ];
    };
  };
  testScript = ''
    def create_test_machine(oldmachine=None, args={}): # taken from <nixpkgs/nixos/tests/installer.nix>
        machine = create_machine({
          "qemuFlags":
            '-cpu max -m 1024 -virtfs local,path=/nix/store,security_model=none,mount_tag=nix-store,'
            f' -drive file={oldmachine.state_dir}/installed.qcow2,id=drive1,if=none,index=1,werror=report'
            f' -device virtio-blk-pci,drive=drive1',
        } | args)
        driver.machines.append(machine)
        return machine
    start_all()
    ssh_key_path = "/etc/ssh/ssh_host_ed25519_key.pub"
    installer.succeed("clan machines install installed root@installed >&2")
    try:
      installed.shutdown()
    except BrokenPipeError:
      # qemu has already exited
      pass
    new_machine = create_test_machine(oldmachine=installed, args={ "name": "after_install" })
    new_machine.start()
    hostname = new_machine.succeed("hostname").strip()
    assert "nixos-anywhere" == hostname, f"'nixos-anywhere' != '{hostname}'"
  '';
}
