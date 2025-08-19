import React, { useEffect, useState } from 'react';
import './App.css';

function App() {
  const [formData, setFormData] = useState({
    projectName: 'my_flask_app',
    projectPath: '',
    databaseType: 'sqlite',
    databaseConfig: {
      host: 'localhost',
      port: '5432',
      username: '',
      password: '',
      database: ''
    }
  });
  
  const [isRunning, setIsRunning] = useState(false);
  const [output, setOutput] = useState([]);
  const [pythonInstalled, setPythonInstalled] = useState(false);

  useEffect(() => {
    // Python 설치 확인
    checkPythonInstallation();
  }, []);

  const checkPythonInstallation = async () => {
    try {
      const installed = await window.electronAPI.checkPython();
      setPythonInstalled(installed);
    } catch (error) {
      console.error('Python 설치 확인 실패:', error);
      setPythonInstalled(false);
    }
  };

  const handleInputChange = (field, value) => {
    if (field.includes('.')) {
      const [parent, child] = field.split('.');
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...prev[parent],
          [child]: value
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  const handleSelectDirectory = async () => {
    try {
      const path = await window.electronAPI.selectDirectory();
      if (path) {
        setFormData(prev => ({
          ...prev,
          projectPath: path
        }));
      }
    } catch (error) {
      console.error('디렉토리 선택 실패:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!pythonInstalled) {
      alert('Python이 설치되어 있지 않습니다. Python을 먼저 설치해주세요.');
      return;
    }

    if (!formData.projectPath) {
      alert('프로젝트 생성 경로를 선택해주세요.');
      return;
    }

    setIsRunning(true);
    setOutput([]);

    // 출력 리스너 설정
    window.electronAPI.onBuilderOutput((data) => {
      setOutput(prev => [...prev, { type: 'output', content: data }]);
    });

    window.electronAPI.onBuilderError((data) => {
      setOutput(prev => [...prev, { type: 'error', content: data }]);
    });

    try {
      const result = await window.electronAPI.runFlaskBuilder(formData);
      if (result.success) {
        setOutput(prev => [...prev, { type: 'success', content: '프로젝트 생성이 완료되었습니다!' }]);
      }
    } catch (error) {
      setOutput(prev => [...prev, { type: 'error', content: `오류 발생: ${error.message}` }]);
    } finally {
      setIsRunning(false);
      // 리스너 정리
      window.electronAPI.removeAllListeners('builder-output');
      window.electronAPI.removeAllListeners('builder-error');
    }
  };

  const getDatabaseFields = () => {
    switch (formData.databaseType) {
      case 'postgresql':
        return (
          <>
            <div className="form-group">
              <label>호스트:</label>
              <input
                type="text"
                value={formData.databaseConfig.host}
                onChange={(e) => handleInputChange('databaseConfig.host', e.target.value)}
                placeholder="localhost"
              />
            </div>
            <div className="form-group">
              <label>포트:</label>
              <input
                type="text"
                value={formData.databaseConfig.port}
                onChange={(e) => handleInputChange('databaseConfig.port', e.target.value)}
                placeholder="5432"
              />
            </div>
            <div className="form-group">
              <label>사용자명:</label>
              <input
                type="text"
                value={formData.databaseConfig.username}
                onChange={(e) => handleInputChange('databaseConfig.username', e.target.value)}
                placeholder="postgres"
              />
            </div>
            <div className="form-group">
              <label>비밀번호:</label>
              <input
                type="password"
                value={formData.databaseConfig.password}
                onChange={(e) => handleInputChange('databaseConfig.password', e.target.value)}
                placeholder="비밀번호"
              />
            </div>
            <div className="form-group">
              <label>데이터베이스명:</label>
              <input
                type="text"
                value={formData.databaseConfig.database}
                onChange={(e) => handleInputChange('databaseConfig.database', e.target.value)}
                placeholder="flask_app"
              />
            </div>
          </>
        );
      case 'mysql':
        return (
          <>
            <div className="form-group">
              <label>호스트:</label>
              <input
                type="text"
                value={formData.databaseConfig.host}
                onChange={(e) => handleInputChange('databaseConfig.host', e.target.value)}
                placeholder="localhost"
              />
            </div>
            <div className="form-group">
              <label>포트:</label>
              <input
                type="text"
                value={formData.databaseConfig.port}
                onChange={(e) => handleInputChange('databaseConfig.port', e.target.value)}
                placeholder="3306"
              />
            </div>
            <div className="form-group">
              <label>사용자명:</label>
              <input
                type="text"
                value={formData.databaseConfig.username}
                onChange={(e) => handleInputChange('databaseConfig.username', e.target.value)}
                placeholder="root"
              />
            </div>
            <div className="form-group">
              <label>비밀번호:</label>
              <input
                type="password"
                value={formData.databaseConfig.password}
                onChange={(e) => handleInputChange('databaseConfig.password', e.target.value)}
                placeholder="비밀번호"
              />
            </div>
            <div className="form-group">
              <label>데이터베이스명:</label>
              <input
                type="text"
                value={formData.databaseConfig.database}
                onChange={(e) => handleInputChange('databaseConfig.database', e.target.value)}
                placeholder="flask_app"
              />
            </div>
          </>
        );
      case 'sqlserver':
        return (
          <>
            <div className="form-group">
              <label>서버:</label>
              <input
                type="text"
                value={formData.databaseConfig.host}
                onChange={(e) => handleInputChange('databaseConfig.host', e.target.value)}
                placeholder="localhost"
              />
            </div>
            <div className="form-group">
              <label>포트:</label>
              <input
                type="text"
                value={formData.databaseConfig.port}
                onChange={(e) => handleInputChange('databaseConfig.port', e.target.value)}
                placeholder="1433"
              />
            </div>
            <div className="form-group">
              <label>사용자명:</label>
              <input
                type="text"
                value={formData.databaseConfig.username}
                onChange={(e) => handleInputChange('databaseConfig.username', e.target.value)}
                placeholder="sa"
              />
            </div>
            <div className="form-group">
              <label>비밀번호:</label>
              <input
                type="password"
                value={formData.databaseConfig.password}
                onChange={(e) => handleInputChange('databaseConfig.password', e.target.value)}
                placeholder="비밀번호"
              />
            </div>
            <div className="form-group">
              <label>데이터베이스명:</label>
              <input
                type="text"
                value={formData.databaseConfig.database}
                onChange={(e) => handleInputChange('databaseConfig.database', e.target.value)}
                placeholder="flask_app"
              />
            </div>
          </>
        );
      default:
        return <p className="info-text">SQLite는 별도 설정이 필요하지 않습니다.</p>;
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🚀 Flask Builder</h1>
        <p>Flask 프로젝트를 빠르게 생성하는 스마트 스캐폴더</p>
      </header>

      <main className="app-main">
        <div className="form-container">
          <form onSubmit={handleSubmit}>
            <div className="form-section">
              <h2>📁 프로젝트 설정</h2>
              
              <div className="form-group">
                <label>프로젝트 이름:</label>
                <input
                  type="text"
                  value={formData.projectName}
                  onChange={(e) => handleInputChange('projectName', e.target.value)}
                  placeholder="my_flask_app"
                  required
                />
              </div>

              <div className="form-group">
                <label>프로젝트 경로:</label>
                <div className="path-input">
                  <input
                    type="text"
                    value={formData.projectPath}
                    onChange={(e) => handleInputChange('projectPath', e.target.value)}
                    placeholder="프로젝트를 생성할 경로를 선택하세요"
                    readOnly
                  />
                  <button
                    type="button"
                    onClick={handleSelectDirectory}
                    className="btn-secondary"
                  >
                    폴더 선택
                  </button>
                </div>
              </div>
            </div>

            <div className="form-section">
              <h2>🗄️ 데이터베이스 설정</h2>
              
              <div className="form-group">
                <label>데이터베이스 타입:</label>
                <select
                  value={formData.databaseType}
                  onChange={(e) => handleInputChange('databaseType', e.target.value)}
                >
                  <option value="sqlite">SQLite (기본)</option>
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                  <option value="sqlserver">SQL Server</option>
                </select>
              </div>

              {getDatabaseFields()}
            </div>

            <div className="form-actions">
              <button
                type="submit"
                disabled={isRunning || !pythonInstalled}
                className="btn-primary"
              >
                {isRunning ? '생성 중...' : '프로젝트 생성'}
              </button>
            </div>
          </form>
        </div>

        <div className="output-container">
          <h2>📋 실행 로그</h2>
          
          {!pythonInstalled && (
            <div className="warning">
              ⚠️ Python이 설치되어 있지 않습니다. Python을 먼저 설치해주세요.
            </div>
          )}

          <div className="output-log">
            {output.length === 0 ? (
              <p className="info-text">프로젝트 생성을 시작하면 로그가 여기에 표시됩니다.</p>
            ) : (
              output.map((item, index) => (
                <div key={index} className={`log-entry ${item.type}`}>
                  {item.content}
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
