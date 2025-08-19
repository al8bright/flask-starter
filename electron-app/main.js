const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'assets/icon.png'),
    titleBarStyle: 'default',
    show: false
  });

  // 개발 모드에서는 로컬 서버, 프로덕션에서는 빌드된 파일
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist/index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC 핸들러들
ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: '프로젝트 생성 경로 선택'
  });
  
  if (!result.canceled) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('run-flask-builder', async (event, config) => {
  return new Promise((resolve, reject) => {
    const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
    
    // 개발 모드와 프로덕션 모드에서 다른 경로 사용
    let scriptPath, cwd;
    if (process.env.NODE_ENV === 'development') {
      scriptPath = path.join(__dirname, '..', 'main.py');
      cwd = path.join(__dirname, '..');
    } else {
      // 프로덕션 모드에서는 앱 내부의 Python 파일 사용
      scriptPath = path.join(process.resourcesPath, 'python', 'main.py');
      cwd = path.join(process.resourcesPath, 'python');
    }
    
    const child = spawn(pythonPath, [scriptPath], {
      cwd: cwd,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let output = '';
    let error = '';

    child.stdout.on('data', (data) => {
      output += data.toString();
      mainWindow.webContents.send('builder-output', data.toString());
    });

    child.stderr.on('data', (data) => {
      error += data.toString();
      mainWindow.webContents.send('builder-error', data.toString());
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve({ success: true, output });
      } else {
        reject({ success: false, error });
      }
    });

    // 설정을 stdin으로 전달
    const configString = JSON.stringify(config) + '\n';
    child.stdin.write(configString);
    child.stdin.end();
  });
});

ipcMain.handle('check-python', async () => {
  return new Promise((resolve) => {
    const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
    const child = spawn(pythonPath, ['--version']);
    
    child.on('close', (code) => {
      resolve(code === 0);
    });
  });
});
