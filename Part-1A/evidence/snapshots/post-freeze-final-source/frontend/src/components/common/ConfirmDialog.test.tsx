import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ConfirmDialog } from './ConfirmDialog'

function setup() {
  const onConfirm = vi.fn()
  const onCancel = vi.fn()
  render(
    <ConfirmDialog
      title="Delete expense"
      message="Delete this expense?"
      confirmLabel="Delete"
      onConfirm={onConfirm}
      onCancel={onCancel}
    />,
  )
  return { onConfirm, onCancel }
}

describe('ConfirmDialog', () => {
  it('is a labelled dialog', () => {
    setup()
    const dialog = screen.getByRole('dialog', { name: 'Delete expense' })
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByText('Delete this expense?')).toBeInTheDocument()
  })

  it('closes on Escape', async () => {
    const { onCancel, onConfirm } = setup()
    await userEvent.keyboard('{Escape}')
    expect(onCancel).toHaveBeenCalledTimes(1)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('calls onConfirm from the confirm button', async () => {
    const { onCancel, onConfirm } = setup()
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(onCancel).not.toHaveBeenCalled()
  })

  it('calls onCancel from the cancel button', async () => {
    const { onCancel, onConfirm } = setup()
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onCancel).toHaveBeenCalledTimes(1)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('keeps keyboard focus inside the dialog', async () => {
    setup()
    const dialog = screen.getByRole('dialog')
    for (let i = 0; i < 4; i += 1) {
      await userEvent.tab()
      expect(dialog.contains(document.activeElement)).toBe(true)
    }
    await userEvent.tab({ shift: true })
    expect(dialog.contains(document.activeElement)).toBe(true)
  })
})
