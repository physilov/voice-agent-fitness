import type { UIComponent } from './types'

interface ChatResponse {
  text: string
  ui_components: UIComponent[]
}

export async function sendMessage(
  phoneNumber: string,
  message: string,
  image?: File,
): Promise<ChatResponse> {
  const form = new FormData()
  form.append('phone_number', phoneNumber)
  form.append('message', message)
  if (image) form.append('image', image)

  const res = await fetch('/web/chat', { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Server error: ${res.status}`)
  return res.json()
}
