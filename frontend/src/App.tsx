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
    const apiUrl = import.meta.env.VITE_API_URL.replace(/\/+$/, '')

    const response = await fetch(`${apiUrl}/analyze`, {
    
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
       WayFinder
    </h1>

   


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
        Agent Output
      </h2>

      <p>
        {summary || "Your AI summary will appear here."}
      </p>

    </div>

  </div>
  )

}
export default App

  