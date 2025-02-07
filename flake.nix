{
  description = "Command-line interface for ChatGPT, Claude and Bard";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = import nixpkgs {inherit system;};

      python = pkgs.python3.withPackages (ps:
        with ps; [
          pydantic
          anthropic
          attrs
          black
          cohere
          google-generativeai
          openai
          prompt-toolkit
          pytest
          pyyaml
          rich
          typing-extensions
        ]);
    in {
      devShells.default = pkgs.mkShell {
        packages = [
          python
          pkgs.uv
        ];
      };
      packages = rec {
        default = gpt-cli;
        gpt-cli = pkgs.callPackage ./package.nix {};
      };
    });
}
