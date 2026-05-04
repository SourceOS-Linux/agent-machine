class AgentMachine < Formula
  desc "SourceOS Agent Machine local and cluster node substrate CLI"
  homepage "https://github.com/SourceOS-Linux/agent-machine"
  url "https://github.com/SourceOS-Linux/agent-machine.git", branch: "main"
  version "0.1.0-dev"
  license "MIT"
  head "https://github.com/SourceOS-Linux/agent-machine.git", branch: "main"

  def install
    bin.install "bin/agent-machine"
    chmod 0755, bin/"agent-machine"

    pkgshare.install "contracts"
    pkgshare.install "docs"
    pkgshare.install "examples"
    pkgshare.install "src"
    pkgshare.install "pyproject.toml"
    pkgshare.install "requirements-dev.txt"
  end

  def caveats
    <<~EOS
      Agent Machine installed the bootstrap CLI:
        agent-machine version
        agent-machine paths
        agent-machine doctor --format json
        agent-machine probe --format json

      This formula installs contracts, docs, examples, and Python package source under:
        #{pkgshare}

      The bootstrap CLI can delegate render commands to the installed package source:
        agent-machine render plan <agentpod.json> --pretty
        agent-machine render quadlet <agentpod.json>
        agent-machine render k8s <agentpod.json>

      Render commands require the Python dependencies listed in:
        #{pkgshare}/requirements-dev.txt

      Runtime directories are not created automatically yet. The future installer
      lane will manage /etc/agent-machine, /var/lib/agent-machine, and
      /run/agent-machine through SourceOS policy-aware setup commands.
    EOS
  end

  test do
    assert_match "agent-machine", shell_output("#{bin}/agent-machine version")
    doctor = shell_output("#{bin}/agent-machine doctor --format json")
    assert_match '"kind": "AgentMachineDoctor"', doctor
    assert_match '"bootstrapOnly": true', doctor
    probe = shell_output("#{bin}/agent-machine probe --format json")
    assert_match '"kind": "AgentMachineProbe"', probe
    assert_match '"secretValuesIncluded": false', probe
    assert_predicate pkgshare/"src/agent_machine/cli.py", :exist?
    assert_predicate pkgshare/"requirements-dev.txt", :exist?
  end
end
