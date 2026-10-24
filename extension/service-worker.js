chrome.runtime.onInstalled.addListener(async () => {
  await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});
chrome.action.onClicked.addListener(async (tab) => {
  if (tab && tab.windowId) await chrome.sidePanel.open({ windowId: tab.windowId });
});