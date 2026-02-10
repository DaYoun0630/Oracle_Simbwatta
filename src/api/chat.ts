const BASE_URL = import.meta.env.VITE_API_BASE_URL

console.log("API BASE URL:", BASE_URL)

export async function sendChat(
  userMessage: string,
  modelResult: any,
  state?: any
) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_message: userMessage,
      model_result: modelResult,
      state,
    }),
  })

  if (!res.ok) {
    throw new Error("Chat API failed")
  }

  return res.json()
}
