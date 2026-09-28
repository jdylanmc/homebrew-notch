cask "notch-pocket" do
  version "0.1.0"
  sha256 "f7337a53af778840be6b42f977be1b5d5d5d651609dcd0061bfef5a355ee1f11"

  url "https://github.com/jdylanmc/notch/releases/download/notch-pocket-v#{version}/notch-pocket-#{version}.dmg"
  name "Notch Pocket"
  desc "Media controls and a file shelf in the macOS notch"
  homepage "https://github.com/jdylanmc/notch"

  depends_on macos: ">= :sonoma"

  app "notch-pocket.app"
end
