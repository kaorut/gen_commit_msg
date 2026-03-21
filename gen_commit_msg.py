import subprocess
import sys


def main() -> int:
	result = subprocess.run(
		["git", "diff"],
		capture_output=True,
		text=True,
		encoding="utf-8",
		errors="replace",
	)

	if result.returncode != 0:
		sys.stderr.write(result.stderr)
		return result.returncode

	sys.stdout.write(result.stdout)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
