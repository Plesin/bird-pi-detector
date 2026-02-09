// Bird Viewer - Tab and Gallery Management Module

const panels = document.querySelectorAll('.tab-panel')
const tabs = document.querySelectorAll('.tab-link')
const defaultTab = 'photos'

const setActiveTab = (tabId) => {
  panels.forEach((panel) => {
    panel.classList.toggle('active', panel.dataset.tab === tabId)
  })
  tabs.forEach((tab) => {
    const isActive = tab.dataset.tab === tabId
    tab.classList.toggle('active', isActive)
    tab.setAttribute('aria-selected', String(isActive))
    tab.setAttribute('tabindex', isActive ? '0' : '-1')
  })

  const liveImage = document.querySelector('.live-feed')
  const liveSpinner = document.querySelector('.live-spinner')
  if (liveImage) {
    if (tabId === 'live') {
      liveSpinner?.classList.add('show')
      liveImage.src = liveImage.dataset.src
      liveImage.onload = () => {
        liveSpinner?.classList.remove('show')
      }
    } else {
      liveImage.removeAttribute('src')
      liveSpinner?.classList.remove('show')
    }
  }
}

tabs.forEach((tab) => {
  tab.addEventListener('click', (event) => {
    event.preventDefault()
    const tabId = tab.dataset.tab
    setActiveTab(tabId)
    history.replaceState(null, '', `#${tabId}`)
  })
})

const initialTab = window.location.hash.replace('#', '') || defaultTab
setActiveTab(initialTab)

document.querySelectorAll('.delete-form').forEach((form) => {
  form.addEventListener('submit', async (event) => {
    event.preventDefault()

    if (!confirm('Delete this file?')) {
      return
    }

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'fetch',
        },
      })

      if (!response.ok) {
        alert('Delete failed. Please try again.')
        return
      }

      const card = form.closest('.gallery-item')
      if (card) {
        card.remove()
      }
    } catch (error) {
      alert('Delete failed. Please try again.')
    }
  })
})

const photoDialog = document.getElementById('photo-dialog')
const dialogImage = document.getElementById('photo-dialog-image')
const dialogTitle = document.getElementById('photo-dialog-title')
const dialogClose = document.querySelector('.dialog-close')

document.querySelectorAll('.photo-thumb').forEach((button) => {
  button.addEventListener('click', () => {
    dialogImage.src = button.dataset.full
    dialogTitle.textContent = button.dataset.title || ''
    photoDialog.showModal()
  })
})

dialogClose.addEventListener('click', () => {
  photoDialog.close()
})

photoDialog.addEventListener('click', (event) => {
  if (event.target === photoDialog) {
    photoDialog.close()
  }
})
