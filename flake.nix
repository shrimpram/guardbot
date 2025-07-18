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
            buildInputs = [
              black

              python313
              python313Packages.flask
              python313Packages.python-dotenv
              python313Packages.slack-sdk
            ];
            shellHook = ''
              if [ ! -d .venv ]; then
                echo "Creating Python venv…"
                python -m venv .venv
              fi
              # activate it every time
              source .venv/bin/activate
            '';
          };
      }
    );
}
