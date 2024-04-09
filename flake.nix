{
  description = "Description for the project";

  inputs = {
    nixpkgs.url = "github:cachix/devenv-nixpkgs/rolling";
    flake-parts.url = "github:hercules-ci/flake-parts";
    devenv.url = "github:cachix/devenv";
    nix2container.url = "github:nlewo/nix2container";
    nix2container.inputs.nixpkgs.follows = "nixpkgs";
    mk-shell-bin.url = "github:rrbutani/nix-mk-shell-bin";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  nixConfig = {
    extra-trusted-public-keys = "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw=";
    extra-substituters = "https://devenv.cachix.org";
  };

  outputs = inputs @ {flake-parts, ...}:
    flake-parts.lib.mkFlake {inherit inputs;} {
      imports = [
        inputs.devenv.flakeModule
      ];
      systems = ["x86_64-linux" "i686-linux" "x86_64-darwin" "aarch64-linux" "aarch64-darwin"];

      perSystem = {
        config,
        self',
        inputs',
        pkgs,
        system,
        ...
      }: {
        # Per-system attributes can be defined here. The self' and inputs'
        # module parameters provide easy access to attributes of the same
        # system.

        # needed for devenv up
        packages.devenv-up = self'.devShells.default.config.procfileScript;

        # Equivalent to  inputs'.nixpkgs.legacyPackages.hello;
        packages.default = (inputs.poetry2nix.lib.mkPoetry2Nix {inherit pkgs;}).mkPoetryApplication {projectDir = ./.;};

        devenv.shells.default = {
          name = "taskschedule";

          imports = [
            # This is just like the imports in devenv.nix.
            # See https://devenv.sh/guides/using-with-flake-parts/#import-a-devenv-module
            # ./devenv-foo.nix
          ];

          # https://devenv.sh/reference/options/
          packages = [
            config.packages.default
            pkgs.hello
          ];

          enterShell = ''
            hello
          '';

          pre-commit.hooks = {
            alejandra.enable = true;
            black.enable = true;
            mypy.enable = true;
            ruff.enable = true;
            check-toml.enable = true;
            taplo.enable = true;
          };

          languages.python = {
            enable = true;
            poetry = {
              enable = true;
              activate.enable = true;
              install.enable = true;
            };
          };
        };
      };
      flake = {
        # The usual flake attributes can be defined here, including system-
        # agnostic ones like nixosModule and system-enumerating ones, although
        # those are more easily expressed in perSystem.
      };
    };
}
