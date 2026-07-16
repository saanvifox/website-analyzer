import {useState} from 'react'
import './App.css'


function App() {

  const [url, setUrl] = useState("")
  const [task, setTask] = useState("")
  const [summary, setSummary] = useState("")
  const [loading, setLoading] = useState(false)

  async function analyzeWebsite() {
  setLoading(true)

  try {
    const response = await fetch("http://127.0.0.1:8000/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url,
        task,
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    setSummary(data.summary)
  } catch (err) {
    console.error(err)
    setSummary("Something went wrong while analyzing the website.")
  } finally {
    setLoading(false)
  }
}

  return (
  <div className="container">

    <h1>
      🌐 Website Analyzer
    </h1>

    <p className="subtitle">
      Analyze websites using AI-powered insights
    </p>


    <div className="card">

      <label>
        Website URL
      </label>

      <input
        type="text"
        placeholder="https://example.com"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
      />


      <label>
        Task
      </label>

      <input
        type="text"
        placeholder="Summarize this website"
        value={task}
        onChange={(e) => setTask(e.target.value)}
      />


      <button onClick={analyzeWebsite}>
        {loading ? "Analyzing..." : "Analyze Website"}
      </button>

    </div>


    <div className="result">

      <h2>
        AI Summary
      </h2>

      <p>
        {summary || "Your AI summary will appear here."}
      </p>

    </div>

  </div>
  )

}
export default App

  