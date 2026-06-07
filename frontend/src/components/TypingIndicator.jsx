export default function TypingIndicator() {
  return (
    <div className="message-wrapper assistant">
      <div className="avatar assistant-avatar">VM</div>
      <div className="bubble assistant-bubble typing-bubble">
        <div className="typing-dots">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  )
}
