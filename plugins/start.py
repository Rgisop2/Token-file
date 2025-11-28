from config import (
    TG_BOT_TOKEN,
    API_HASH,
    APP_ID,
    CHANNEL_ID,
    IS_VERIFY,
    VERIFY_EXPIRE_1,
    VERIFY_EXPIRE_2,
    SHORTLINK_URL_1,
    SHORTLINK_API_1,
    SHORTLINK_URL_2,
    SHORTLINK_API_2,
    VERIFY_GAP_TIME,
    VERIFY_IMAGE,
    TUT_VID,
    START_MSG,
)
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from helper_func import subscribed, encode, decode, get_messages, get_shortlink, get_verify_status, update_verify_status, get_exp_time, get_verify_image, get_batch_verify_image
from database.database import add_user, del_user, full_userbase, present_user, db_get_link
from shortzy import Shortzy


def is_dual_verification_enabled():
    """Check if dual verification system is fully configured"""
    return bool(SHORTLINK_URL_2 and SHORTLINK_API_2)


async def send_verification_message(message, caption_text, verify_image, reply_markup):
    """Send verification message with photo - always tries to send image first"""
    if verify_image and isinstance(verify_image, str) and verify_image.strip():
        try:
            await message.reply_photo(
                photo=verify_image,
                caption=caption_text,
                reply_markup=reply_markup,
                quote=True
            )
            return
        except Exception as e:
            print(f"[v0] Photo failed with: {e}. Retrying with text message...")
    
    try:
        await message.reply(
            text=caption_text,
            reply_markup=reply_markup,
            quote=True
        )
    except Exception as e:
        print(f"[v0] Text message failed: {e}")
        pass


@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    if not await present_user(id):
        await add_user(id)
    
    args = message.command
    
    if len(args) > 1:
        payload = args[1]
        decoded = await decode(payload)
        
        # Check if it's a verification link
        if decoded.startswith("verify_"):
            token = decoded.replace("verify_", "")
            verify_status = await get_verify_status(id)
            
            # Verify token matches
            if verify_status.get('verify_token') == token:
                # Update verification status
                if verify_status.get('current_step') == 0:
                    # First verification complete
                    verify_status['current_step'] = 1
                    verify_status['verify1_expiry'] = int(__import__('time').time()) + VERIFY_EXPIRE_1
                    verify_status['gap_expiry'] = int(__import__('time').time()) + VERIFY_GAP_TIME
                elif verify_status.get('current_step') == 1:
                    # Second verification complete
                    verify_status['current_step'] = 2
                    verify_status['verify2_expiry'] = int(__import__('time').time()) + VERIFY_EXPIRE_2
                
                await update_verify_status(id, verify_status)
                await message.reply("✅ Verification successful! You can now access files.", quote=True)
            else:
                await message.reply("❌ Invalid or expired verification token.", quote=True)
            return
        
        # Regular file link
        parts = decoded.split('-')
        if len(parts) >= 2:
            msg_id = int(parts[1]) if parts[1].isdigit() else None
            if msg_id:
                verify_status = await get_verify_status(id)
                step = verify_status.get('current_step', 0)
                access_allowed = verify_status.get('is_verified', False)
                access_type = None
                
                if step == 2:
                    access_allowed = True
                elif step == 1:
                    access_type = 'require_step2'
                elif step == 0:
                    access_type = 'require_step1'
                
                if not access_allowed and IS_VERIFY and access_type:
                    if access_type == 'require_step1':
                        token = ''.join(__import__('random').choices(__import__('string').ascii_letters + __import__('string').digits, k=10))
                        await update_verify_status(id, verify_token=token, is_verified=False, current_step=0)
                        link = await get_shortlink(SHORTLINK_URL_1, SHORTLINK_API_1, f'https://telegram.dog/{client.username}?start=verify_{token}')
                        
                        if link and isinstance(link, str) and link.startswith(('http://', 'https://', 'tg://')):
                            btn = [
                                [
                                    InlineKeyboardButton("• OPEN LINK ➜", url=link),
                                    InlineKeyboardButton("TUTORIAL ➜", url=TUT_VID) if TUT_VID and isinstance(TUT_VID, str) and TUT_VID.startswith(('http://', 'https://', 'tg://')) else None
                                ]
                            ]
                            btn = [[b for b in row if b is not None] for row in btn]
                            
                            file_id = decoded if decoded.startswith("get-") else f"get-{msg_id * abs(client.db_channel.id)}"
                            verify_image = await get_verify_image(file_id)
                            user_first = message.from_user.first_name if message.from_user else "User"
                            caption_text = f"📊 HEY {user_first},\n‼ GET ALL FILES IN A SINGLE LINK ‼\n≛ YOUR LINK IS READY, KINDLY CLICK ON\nOPEN LINK BUTTON.."
                            await send_verification_message(message, caption_text, verify_image, InlineKeyboardMarkup(btn))
                        else:
                            await message.reply(f"Your token is expired or not verified. Complete verification to access files.\n\nToken Timeout: {get_exp_time(VERIFY_EXPIRE_1)}\n\nError: Could not generate verification link. Please try again.", quote=True)
                        return
                    
                    elif access_type == 'require_step2':
                        token = ''.join(__import__('random').choices(__import__('string').ascii_letters + __import__('string').digits, k=10))
                        await update_verify_status(id, verify_token=token, is_verified=False, current_step=1)
                        link = await get_shortlink(SHORTLINK_URL_2, SHORTLINK_API_2, f'https://telegram.dog/{client.username}?start=verify_{token}')
                        
                        if link and isinstance(link, str) and link.startswith(('http://', 'https://', 'tg://')):
                            btn = [
                                [
                                    InlineKeyboardButton("• OPEN LINK ➜", url=link),
                                    InlineKeyboardButton("TUTORIAL ➜", url=TUT_VID) if TUT_VID and isinstance(TUT_VID, str) and TUT_VID.startswith(('http://', 'https://', 'tg://')) else None
                                ]
                            ]
                            btn = [[b for b in row if b is not None] for row in btn]
                            
                            file_id = decoded if decoded.startswith("get-") else f"get-{msg_id * abs(client.db_channel.id)}"
                            verify_image = await get_batch_verify_image(file_id)
                            user_first = message.from_user.first_name if message.from_user else "User"
                            caption_text = f"📊 HEY {user_first},\n‼ GET ALL FILES IN A SINGLE LINK ‼\n≛ YOUR LINK IS READY, KINDLY CLICK ON\nOPEN LINK BUTTON.."
                            await send_verification_message(message, caption_text, verify_image, InlineKeyboardMarkup(btn))
                        else:
                            await message.reply(f"Complete second verification to continue accessing files.\n\nToken Timeout: {get_exp_time(VERIFY_EXPIRE_2)}\n\nError: Could not generate verification link. Please try again.", quote=True)
                        return
                
                # User is verified or verification not required
                await message.reply("✅ Access granted! Files available in the channel.", quote=True)
                return
    
    # Normal start command
    user_first = message.from_user.first_name if message.from_user else "User"
    start_msg = START_MSG.format(first=user_first)
    await message.reply(start_msg)
