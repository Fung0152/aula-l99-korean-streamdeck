# AULA L99 setup and usage

## Download and prepare

1. Download **L99StreamDeck-Windows-v0.1.0.zip** from the [v0.1.0 release](https://github.com/Fung0152/aula-l99-korean-streamdeck/releases/tag/v0.1.0).
2. Extract the entire ZIP. Keep `L99StreamDeck.exe`, `_internal`, `assets` and `vendor` together; do not run only the EXE from inside the archive.
3. Place the folder at its permanent location before enabling startup at sign-in.
4. Connect the keyboard by USB and select wired USB mode (Fn+4 on the development device). Enable NumLock.
5. Fully exit any older L99 connection program, then run `L99StreamDeck.exe`. Its connection turns on automatically.

First-time users must perform the full installation below. If this distribution's compatible integrated layout is already installed, proceed to everyday use.

## Configure shortcuts

The rows map to the display from left to right: row 1 is numpad 0–3; row 2 is 4–7; row 3 is 8, 9, divide, then Back.

- Enter a short display name in **이름 (Name)**.
- Use **파일 경로 (File path)** or edit the target field directly. Example: `C:\Windows\System32\notepad.exe`.
- Enter `https://www.youtube.com/` or `https://chatgpt.com/` in the same field to open it in the default browser.
- **아이콘 설정 (Set icon)** selects an image; **기본 아이콘 (Default icon)** returns to the Windows file icon. Web targets use a generic web icon.
- Select **설정 저장 (Save settings)**. The initial GPT example may not match an installed app on your PC, so choose your own program or URL.

## First full installation

**A full update may overwrite photos, GIFs and backgrounds stored on the device. Do not proceed without considering any content you need to preserve. The distribution image is not a readback backup.**

1. Configure and save your shortcut names, targets and icons.
2. Select **펌웨어 적용 (Apply firmware)** and confirm file generation.
3. In USB mode, hold **Fn+Space for about five seconds** to turn off the display. Wait for USB reconnection.
4. Click **Start once in the original updater**. Opening the updater alone does not begin writing.
5. Keep USB power connected and wait for **100% / OK**, approximately ten minutes on the development device.
6. Only after that confirmation, close the updater and restart the keyboard. Reselect USB mode if necessary.
7. The editor reconnects when the updater closes. Enter Stream Deck from the keyboard's Home screen.

If English menus remain visible, check the language setting. Korean replaces the original Chinese language bank; the English bank is retained.

The separate **L99-integrated-screen-v0.1.0.zip** contains the default integrated screen and original updater for direct installation or recovery. Using the Windows editor's full-update button is sufficient for normal initial setup; you do not need to flash both packages sequentially.

## Everyday use

1. Run the application, or allow it to start in the tray at Windows sign-in.
2. Confirm the connection is on; select **연결 켜기 (Connect)** if needed.
3. Enter Stream Deck from Home. If you reconnected the PC program while the display was already on the shortcut page, go Back and enter again.
4. Touch a tile to launch its PC target. Use the lower-right Back tile to return Home.

The PC application must remain running, including in the tray. While connected, numpad minus/plus are reserved as enter/exit signals. In Stream Deck mode, physical numpad 0–9 and divide also launch shortcuts. Back restores normal digits/divide; Disconnect or Full exit releases the reservations.

## Choose the right operation

| Change | Operation | Display off? | Typical time |
|---|---|---|---|
| Target path or URL only | Save settings | No | Immediate |
| Displayed names or icons | Apply icons | Yes | 2–3 minutes |
| Initial layout, full layout change or recovery | Apply firmware | Yes | About 10 minutes |

For an icon update: save your changes, close the original updater, turn off the display using Fn+Space in USB mode, then select **아이콘 적용 (Apply icons)** and confirm readiness. Wait through existing-image checks, the 384 KB transfer and full verification. Keep power connected. After the completion message, restart the keyboard; the PC connection resumes automatically.

An unknown baseline is rejected before image data is written. Another layout or vendor-tool media changes can alter that baseline. Do not blindly overwrite content with a full update. A failure during actual writing may require recovery with the original updater; failures are not automatically retried.

## Startup, tray and exit

- Enable **Windows 시작 시 자동 실행** to register startup for the current Windows account. It starts in the tray after sign-in. Uncheck to remove registration. If you move the program, set startup again at its new location.
- Minimize sends the window to the tray without disconnecting.
- X offers Move to tray, Full exit and Cancel.
- Use the tray's default action or Open menu item to restore the editor. Its menu also offers Full exit.
- Launching the same version again restores the existing window. Older versions must be exited separately.
- Local settings and icons live under `data/`. Keep a copy when upgrading and never publish that folder: it can contain personal paths.

## Troubleshooting

- No launch: check Connect, NumLock and the target path; return Home and re-enter Stream Deck.
- Missing minus/plus typing: Disconnect when normal typing of these reserved keys is needed.
- Numpad launches apps: leave Stream Deck using Back.
- Start unavailable: check USB mode, display-off state and USB reconnection, and close competing updater/serial programs.
- Saved name/icon not shown: Save settings updates PC targets; use Apply icons to update the display.
- CRC or transfer error: read the error and do not repeatedly write. Baseline mismatches stop before writing; an interrupted write may need full recovery.
- CPU/GPU/weather/humidity readings do not refresh: the real-time telemetry helper is not included in this distribution and is separate from the Stream Deck connection.

Development and tests used one L99 in USB mode, reporting V1.29. Other hardware revisions and wireless mode are unverified. The newly rebuilt factory-default distribution image has not itself undergone another flash test.
