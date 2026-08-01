import Header from './components/Header';
import ComplaintForm from './components/ComplaintForm';
import AiCopilot from './components/AiCopilot';
import ToastContainer from './components/Toast';
import './App.css';

export default function App() {
  return (
    <div className="app-root">
      <Header />
      <main className="app-main">
        <ComplaintForm />
        <AiCopilot />
      </main>
      <ToastContainer />
    </div>
  );
}
