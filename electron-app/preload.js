const { contextBridge, ipcRenderer } = require('electron');

// 안전한 API 노출
contextBridge.exposeInMainWorld('electronAPI', {
  // 디렉토리 선택
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  
  // Flask Builder 실행
  runFlaskBuilder: (config) => ipcRenderer.invoke('run-flask-builder', config),
  
  // Python 설치 확인
  checkPython: () => ipcRenderer.invoke('check-python'),
  
  // 빌더 출력 수신
  onBuilderOutput: (callback) => {
    ipcRenderer.on('builder-output', (event, data) => callback(data));
  },
  
  // 빌더 에러 수신
  onBuilderError: (callback) => {
    ipcRenderer.on('builder-error', (event, data) => callback(data));
  },
  
  // 리스너 제거
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  }
});
