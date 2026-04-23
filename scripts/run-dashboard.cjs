/**
 * npm run dev → FastAPI 대시보드 (frontend/server.py)
 * Windows: .venv\Scripts\python.exe 우선
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const serverPy = path.join(root, 'frontend', 'server.py');

const winVenv = path.join(root, '.venv', 'Scripts', 'python.exe');
const unixVenv = path.join(root, '.venv', 'bin', 'python');

let python = process.env.PYTHON || 'python';
if (fs.existsSync(winVenv)) python = winVenv;
else if (fs.existsSync(unixVenv)) python = unixVenv;

const args = [serverPy, '--host', '127.0.0.1', '--port', '8765'];
if (process.argv.includes('--open')) args.push('--open');

const child = spawn(python, args, {
  cwd: root,
  stdio: 'inherit',
  shell: false,
});

child.on('error', (err) => {
  console.error('실행 실패:', err.message);
  console.error('Python 경로:', python);
  process.exit(1);
});

child.on('exit', (code) => process.exit(code ?? 0));
