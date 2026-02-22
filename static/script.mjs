// Bird Viewer - Tab and Gallery Management Module

const photoDialog = document.getElementById('photo-dialog')
const dialogImage = document.getElementById('photo-dialog-image')
const dialogTitle = document.getElementById('photo-dialog-title')
const dialogExif = document.getElementById('photo-dialog-exif')

// ==================== Thumbnail Size ====================
const THUMB_WIDTHS = { s: 320, m: 640, l: 1280 }

function applyThumbSize(size, container = document) {
  const width = THUMB_WIDTHS[size]
  container.querySelectorAll('img[data-path]').forEach((img) => {
    img.src = `/thumbs/${size}/${img.dataset.path}`
  })
  container
    .querySelectorAll('.gallery .card, .gallery-placeholder .card')
    .forEach((card) => {
      card.style.width = `min(${width}px, 100%)`
    })
}

const allSizeButtons = document.querySelectorAll(
  '#thumb-size-picker [data-size], #video-thumb-size-picker [data-size]',
)

function setThumbSize(size) {
  localStorage.setItem('thumbSize', size)
  allSizeButtons.forEach((b) =>
    b.classList.toggle('btn-active', b.dataset.size === size),
  )
  applyThumbSize(size)
}

allSizeButtons.forEach((btn) => {
  btn.addEventListener('click', () => setThumbSize(btn.dataset.size))
})

// Apply saved size on load
const savedSize = localStorage.getItem('thumbSize') || 'm'
setThumbSize(savedSize)

// ==================== Tab Management ====================
// Handle DaisyUI tab switching with live feed loading
const tabRadios = document.querySelectorAll('input[name="tab_gallery"]')
const defaultTab = 'photos'

const handleTabChange = (tabId) => {
  const liveImage = document.querySelector('.live-feed')
  const liveSpinner = document.querySelector('.live-spinner')

  if (tabId === 'live') {
    if (liveImage) {
      liveSpinner?.classList.add('show')
      liveImage.src = liveImage.dataset.src
      liveImage.onload = () => {
        liveSpinner?.classList.remove('show')
      }
    }
  } else {
    if (liveImage) {
      liveImage.removeAttribute('src')
      liveSpinner?.classList.remove('show')
    }
  }

  history.replaceState(null, '', `#${tabId}`)
}

tabRadios.forEach((radio) => {
  radio.addEventListener('change', (event) => {
    if (event.target.checked) {
      const tabId = event.target.getAttribute('data-tab')
      handleTabChange(tabId)
    }
  })
})

// Handle initial tab from URL hash
const initialTab = window.location.hash.replace('#', '') || defaultTab
const initialRadio = document.querySelector(
  `input[name="tab_gallery"][data-tab="${initialTab}"]`,
)
if (initialRadio) {
  initialRadio.checked = true
  // Trigger change event to load live feed if needed
  initialRadio.dispatchEvent(new Event('change', { bubbles: true }))
}

// ==================== Photo Dialog ====================
function handlePhotoClick() {
  dialogImage.src = this.dataset.full
  dialogTitle.textContent = this.dataset.title || ''

  // Display EXIF data if available
  const exifStr = this.dataset.exif || ''
  if (exifStr) {
    dialogExif.textContent = exifStr
    dialogExif.style.display = 'block'
  } else {
    dialogExif.style.display = 'none'
  }

  photoDialog.showModal()
}

photoDialog.addEventListener('click', (event) => {
  // Close when clicking outside the modal box
  if (event.target === photoDialog) {
    photoDialog.close()
  }
})

// ==================== Delete Handling ====================
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

    const card = this.closest('.card')
    if (card) {
      card.remove()
    }
  } catch (error) {
    alert('Delete failed. Please try again.')
  }
}

// ==================== Gallery Event Listeners ====================
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

// ==================== Collapse Event Listeners ====================
// Handle collapse open/close — lazy-load thumbnails on first expand
document.querySelectorAll('.collapse').forEach((collapse) => {
  const checkbox = collapse.querySelector('input[type="checkbox"]')
  if (checkbox) {
    checkbox.addEventListener('change', async () => {
      if (!checkbox.checked) return

      const placeholder = collapse.querySelector(
        '.gallery-placeholder[data-loaded="false"]',
      )
      if (placeholder) {
        const dayKey = placeholder.dataset.dayKey
        const mediaType = placeholder.dataset.mediaType
        try {
          const res = await fetch(`/day/${dayKey}/thumbs?type=${mediaType}`)
          if (res.ok) {
            const currentSize = localStorage.getItem('thumbSize') || 'm'
            placeholder.innerHTML = await res.text()
            placeholder.dataset.loaded = 'true'
            placeholder.className = 'gallery flex flex-wrap gap-4'
            applyThumbSize(currentSize, placeholder)
            attachGalleryListeners(placeholder)
          }
        } catch (_) {
          // will retry on next expand
        }
      } else {
        const gallery = collapse.querySelector('.gallery')
        if (gallery) attachGalleryListeners(gallery)
      }
    })
  }
})

// ==================== Initial Setup ====================
// Attach listeners to pre-loaded galleries (today's expanded section)
document
  .querySelectorAll('.collapse.collapse-open .gallery')
  .forEach((gallery) => {
    attachGalleryListeners(gallery)
  })

// Also handle day-view pages where there's no collapse wrapper
document
  .querySelectorAll('.day-content:not([style*="display: none"]) .gallery')
  .forEach((gallery) => {
    attachGalleryListeners(gallery)
  })
