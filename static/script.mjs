// Bird Viewer - Tab and Gallery Management Module

import PhotoSwipeLightbox from '/static/libs/photoswipe-lightbox.esm.min.js'

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

// ==================== PhotoSwipe Gallery ====================
function initPhotoSwipe(gallery) {
  if (gallery._pswpInitialized) return
  gallery._pswpInitialized = true

  const lightbox = new PhotoSwipeLightbox({
    gallery,
    children: 'a.photo-thumb',
    pswpModule: () => import('/static/libs/photoswipe.esm.min.js'),
  })

  // Read the already-loaded thumbnail's natural size to derive the correct
  // aspect ratio before PhotoSwipe renders anything — no layout shift.
  lightbox.addFilter('itemData', (itemData) => {
    const thumb = itemData.element?.querySelector('img')
    if (thumb?.naturalWidth) {
      // Scale up to a high-res base so PhotoSwipe has room to zoom
      const scale = 1920 / thumb.naturalWidth
      itemData.width = 1920
      itemData.height = Math.round(thumb.naturalHeight * scale)
    }
    return itemData
  })

  lightbox.on('uiRegister', () => {
    lightbox.pswp.ui.registerElement({
      name: 'caption',
      order: 9,
      isButton: false,
      appendTo: 'wrapper',
      onInit: (el, pswp) => {
        pswp.on('change', () => {
          const anchor = pswp.currSlide?.data?.element
          const title = anchor?.dataset?.title || ''
          const exif = anchor?.dataset?.exif || ''
          const parts = [title, exif].filter(Boolean)
          el.innerHTML = parts.length
            ? `<div class="pswp__caption">${parts.join(' • ')}</div>`
            : ''
        })
      },
    })
  })

  lightbox.init()
}

// ==================== Delete Handling ====================
function showErrorToast(message) {
  const toast = document.getElementById('error-toast')
  const text = document.getElementById('error-toast-text')
  if (!toast || !text) return
  text.textContent = message
  toast.classList.remove('hidden')
  setTimeout(() => toast.classList.add('hidden'), 4000)
}

function showDeleteModal() {
  return new Promise((resolve) => {
    const modal = document.getElementById('delete-confirm-modal')
    const confirmBtn = document.getElementById('delete-confirm-btn')
    let confirmed = false

    const onConfirm = () => {
      confirmed = true
      modal.close()
    }

    const onClose = () => {
      confirmBtn.removeEventListener('click', onConfirm)
      modal.removeEventListener('close', onClose)
      resolve(confirmed)
    }

    confirmBtn.addEventListener('click', onConfirm)
    modal.addEventListener('close', onClose)
    modal.showModal()
  })
}

async function handleDelete(event) {
  event.preventDefault()

  const confirmed = await showDeleteModal()
  if (!confirmed) return

  try {
    const response = await fetch(this.action, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'fetch',
      },
    })

    if (!response.ok) {
      showErrorToast('Delete failed. Please try again.')
      return
    }

    const card = this.closest('.card')
    if (card) {
      card.remove()
    }
  } catch (error) {
    showErrorToast('Delete failed. Please try again.')
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

  // Initialize PhotoSwipe for photo galleries
  if (container.querySelector('a.photo-thumb')) {
    initPhotoSwipe(container)
  }
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

// ==================== SSE Auto-Refresh ====================
// Listen for new media events from the server and reload the page automatically.
// If the live stream tab is active, show a banner instead to avoid interrupting it.
function initSSE() {
  if (!window.EventSource) return

  const source = new EventSource('/events')

  source.addEventListener('new-media', () => {
    const toast = document.getElementById('sse-toast')
    const toastText = document.getElementById('sse-toast-text')
    const toastInner = document.getElementById('sse-toast-inner')
    if (!toast || toast.dataset.active) return
    toast.dataset.active = 'true'
    toast.classList.remove('hidden')

    const liveRadio = document.querySelector(
      'input[name="tab_gallery"][data-tab="live"]',
    )
    const onLiveTab = liveRadio?.checked

    if (onLiveTab) {
      toastText.textContent = 'New photos detected — click to refresh'
      toastInner.classList.add('cursor-pointer')
      toastInner.addEventListener('click', () => location.reload())
    } else {
      let seconds = 5
      toastText.textContent = `New photos detected, reloading in ${seconds}s`
      const interval = setInterval(() => {
        seconds -= 1
        toastText.textContent = `New photos detected, reloading in ${seconds}s`
        if (seconds <= 0) {
          clearInterval(interval)
          location.reload()
        }
      }, 1000)
    }
  })

  source.onerror = () => {
    // Browser will automatically reconnect; nothing to do here
  }
}

initSSE()
