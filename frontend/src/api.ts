import type { UIComponent } from './types'

interface ChatResponse {
  text: string
  ui_components: UIComponent[]
}

export async function sendMessage(
  phoneNumber: string,
  message: string,
): Promise<ChatResponse> {
  const res = await fetch('/web/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone_number: phoneNumber, message }),
  })
  if (!res.ok) throw new Error(`Server error: ${res.status}`)
  return res.json()
}
