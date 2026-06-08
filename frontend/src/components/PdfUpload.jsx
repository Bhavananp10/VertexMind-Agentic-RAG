import { useRef } from 'react'

export default function PdfUpload({ isDragging, onFileDrop, onFileSelect }) {
  const inputRef = useRef(null)

  const handleChange = (e) => {
    const file = e.target.files?.[0]
    if (file) onFileSelect(file)
    e.target.value = ''
  }

  // Hidden input exposed to Header's upload button via window event
  if (!isDragging) return (
    <input
      ref={inputRef}
      id="pdf-file-input"
      type="file"
      accept=".pdf,application/pdf"
      style={{ display: 'none' }}
      onChange={handleChange}
    />
  )

  return (
    <>
      <input
        ref={inputRef}
        id="pdf-file-input"
        type="file"
        accept=".pdf,application/pdf"
        style={{ display: 'none' }}
        onChange={handleChange}
      />
      <div className="drop-overlay">
        <div className="drop-box">
          <div className="drop-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m.75 12l3 3m0 0l3-3m-3 3v-6m-1.5-9H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/>
            </svg>
          </div>
          <p className="drop-title">Drop your PDF here</p>
          <p className="drop-sub">Release to start ingestion</p>
        </div>
      </div>
    </>
  )
}
