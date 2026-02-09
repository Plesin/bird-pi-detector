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

// Photo dialog setup
const photoDialog = document.getElementById('photo-dialog')
const dialogImage = document.getElementById('photo-dialog-image')
const dialogTitle = document.getElementById('photo-dialog-title')
const dialogClose = document.querySelector('.dialog-close')

// Day collapsible sections
document.querySelectorAll('.day-toggle-btn').forEach((btn) => {
  btn.addEventListener('click', async (event) => {
    event.preventDefault()
    event.stopPropagation()
    const contentId = btn.dataset.toggle
    const content = document.getElementById(contentId)
    const icon = btn.querySelector('.day-toggle-icon')

    if (content) {
      const isVisible = content.style.display !== 'none'

      if (isVisible) {
        // Collapsing - hide and clear content
        content.style.display = 'none'
        icon.textContent = '▶'
      } else {
        // Expanding - show content
        content.style.display = 'block'
        icon.textContent = '▼'

        // Attach event listeners to newly loaded/visible elements
        attachGalleryListeners(content)
      }
    }
  })
})

function attachGalleryListeners(container) {
  // Attach delete form handlers
  container.querySelectorAll('.delete-form').forEach((form) => {
    if (!form.dataset.listenerAttached) {
      form.addEventListener('submit', handleDelete)
      form.dataset.listenerAttached = 'true'
    }
  })

  // Attach photo dialog handlers
  container.querySelectorAll('.photo-thumb').forEach((button) => {
    if (!button.dataset.listenerAttached) {
      button.addEventListener('click', handlePhotoClick)
      button.dataset.listenerAttached = 'true'
    }
  })
}

async function handleDelete(event) {
  event.preventDefault()

  if (!confirm('Delete this file?')) {
    return
  }

  try {
    const response = await fetch(this.action, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'fetch',
      },
    })

    if (!response.ok) {
      alert('Delete failed. Please try again.')
      return
    }

    const card = this.closest('.gallery-item')
    if (card) {
      card.remove()
    }
  } catch (error) {
    alert('Delete failed. Please try again.')
  }
}

function handlePhotoClick() {
  dialogImage.src = this.dataset.full
  dialogTitle.textContent = this.dataset.title || ''
  photoDialog.showModal()
}

dialogClose.addEventListener('click', () => {
  photoDialog.close()
})

photoDialog.addEventListener('click', (event) => {
  if (event.target === photoDialog) {
    photoDialog.close()
  }
})

// Initial setup: attach listeners to visible galleries (e.g., today's section)
document.querySelectorAll('.day-content').forEach((content) => {
  if (content.style.display !== 'none') {
    attachGalleryListeners(content)
  }
})
