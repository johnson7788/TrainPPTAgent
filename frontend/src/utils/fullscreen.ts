// 进入全屏
export const enterFullscreen = (el = document.documentElement) => {
  if (el.requestFullscreen) el.requestFullscreen()
  else if (el.mozRequestFullScreen) el.mozRequestFullScreen()
  else if (el.webkitRequestFullScreen) el.webkitRequestFullScreen()
  else if (el.msRequestFullscreen) el.msRequestFullscreen()
}

// 退出全屏
export const exitFullscreen = () => {
  if (document.exitFullscreen) document.exitFullscreen()
  else if (document.mozCancelFullScreen) document.mozCancelFullScreen()
  else if (document.webkitExitFullscreen) document.webkitExitFullscreen()
  else if (document.msExitFullscreen) document.msExitFullscreen()
}

// 判断是否全屏
export const isFullscreen = () => {
  const fullscreenElement = 
    document.fullscreenElement ||
    document.mozFullScreenElement ||
    document.webkitFullscreenElement ||
    document.msFullscreenElement ||
    document.webkitCurrentFullScreenElement
  return !!fullscreenElement
}