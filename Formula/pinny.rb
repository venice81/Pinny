class Pinny < Formula
  include Language::Python::Virtualenv

  desc "TUI/CLI wrapper for xcrun simctl location"
  homepage "https://github.com/venice81/Pinny"
  url "https://github.com/venice81/Pinny/archive/refs/tags/0.2.0.tar.gz"
  sha256 "0be0667945326ebc6132664a25702f506e60d0ccecba77536dcdd8b148486238"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "pinny", shell_output("#{bin}/pinny --help")
  end
end
