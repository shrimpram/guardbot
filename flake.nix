{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.05";
    utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      utils,
    }:
    utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
      in
      {
        devShell =
          with pkgs;
          mkShell {
            packages = [
              black
              python313
            ];

            buildInputs = [
              readline
              libffi
              openssl
              git
              openssh
              rsync
            ];

            shellHook = ''
              if [ ! -d .venv ]; then
                python -m venv .venv
              fi
              source .venv/bin/activate
              pip install -r requirements.txt
            '';
          };
      }
    );
}
