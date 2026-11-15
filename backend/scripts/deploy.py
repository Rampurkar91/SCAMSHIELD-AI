"""Portable local/VPS Docker Compose launcher. No cloud credentials required."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description='Build and start ScamShield on http://localhost:8080 using Docker Compose v2.24+.')
    parser.add_argument('--speech-model', action='store_true', help='Operator opt-in: download the base speech model before starting; requires model-host internet access.')
    args = parser.parse_args()
    try:
        subprocess.run(['docker', 'compose', 'version'], cwd=ROOT, check=True)
        subprocess.run([sys.executable, str(ROOT / 'backend/scripts/configure_local.py')], cwd=ROOT, check=True)
        compose = ['docker', 'compose', '-f', 'compose.production.yml']
        subprocess.run([*compose, 'config', '--quiet'], cwd=ROOT, check=True)
        if args.speech_model:
            subprocess.run([*compose, '--profile', 'setup', 'run', '--build', '--rm', 'model-setup'], cwd=ROOT, check=True)
        subprocess.run([*compose, 'up', '-d', '--build'], cwd=ROOT, check=True)
        print('Containers started. Open http://localhost:8080 (or your configured FRONTEND_URL/APP_PORT).')
        print('Check readiness: docker compose -f compose.production.yml ps')
        print('SMTP/provider keys and optional models still need configuration. See docs/EASY_DEPLOY.md.')
    except FileNotFoundError:
        print('Docker Compose is required. Install Docker Desktop or Docker Engine with Compose v2.24+.', file=sys.stderr)
        return 1
    except subprocess.CalledProcessError:
        print('Deployment step failed. Review Docker output above; no deployment success is claimed.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
