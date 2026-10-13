interface Props {
  message: string
}

export default function EmptyState({ message }: Props) {
  return (
    <div className="flex items-center justify-center h-full text-gray-400 text-sm p-8">
      {message}
    </div>
  )
}
