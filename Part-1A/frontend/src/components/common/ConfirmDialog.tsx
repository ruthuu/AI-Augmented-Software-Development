import { useRef } from 'react'
import { Button } from './Button'
import { ModalPanel } from './ModalPanel'

interface ConfirmDialogProps {
  title: string
  message: string
  confirmLabel: string
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({ title, message, confirmLabel, onConfirm, onCancel }: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  return (
    <ModalPanel title={title} onClose={onCancel} initialFocus={cancelRef}>
      <p>{message}</p>
      <div className="modal-actions">
        <Button ref={cancelRef} onClick={onCancel}>
          Cancel
        </Button>
        <Button variant="danger" onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </ModalPanel>
  )
}