class Pinny < Formula
  include Language::Python::Virtualenv

  desc "TUI/CLI wrapper for xcrun simctl location"
  homepage "https://github.com/venice81/Pinny"
  url "https://github.com/venice81/Pinny/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "d5558cd419c8d46bdc958064cb97f963d1ea793866414c025906ec15033512ed"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "pinny", shell_output("#{bin}/pinny --help")
  end
end
