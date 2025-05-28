import discord
from discord.ext import commands
import asyncio
import logging
import traceback

debug_logger = logging.getLogger('debug')
debug_logger.setLevel(logging.DEBUG)

class Cleaner(commands.Cog):
    """Utilities for cleaning up bot messages in chat."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clean", pass_context=True)
    @commands.has_permissions(manage_messages=True)
    async def clean(self, ctx, limit: int = 100, use_bulk: str = "auto"):
        """Removes bot commands and responses from the chat.
        Usage: !clean [number_of_messages_to_check=100] [use_bulk=auto]
        use_bulk options: 'auto', 'yes', 'no'
        Requires 'Manage Messages' permission."""
        
        debug_logger.info("Clean command started with limit=%d, use_bulk=%s", limit, use_bulk)
        
        try:
            # Send initial status message
            debug_logger.debug("Sending status message")
            status_msg = await ctx.send("🧹 Cleaning messages... (This may take some time due to Discord's rate limits)")
            debug_logger.debug("Status message sent: %s", status_msg.id)
            
            # Delete command message
            debug_logger.debug("Deleting command message: %s", ctx.message.id)
            try:
                await ctx.message.delete()
                debug_logger.debug("Command message deleted successfully")
            except discord.errors.NotFound:
                debug_logger.error("Command message not found, may have been deleted already")
            except Exception as e:
                debug_logger.error("Error deleting command message: %s", str(e))
                
            deleted = 0
            
            # Determine if we should use bulk delete
            use_bulk_delete = use_bulk.lower() == "yes"
            if use_bulk.lower() == "auto":
                # In auto mode, we'll use bulk delete if available
                use_bulk_delete = hasattr(ctx.channel, "purge")
                
            debug_logger.debug("Using bulk delete: %s", use_bulk_delete)
            
            if use_bulk_delete:
                # Use bulk delete (more efficient, but only works on messages less than 14 days old)
                debug_logger.debug("Attempting bulk delete")
                def is_bot_or_command(message):
                    return message.author == self.bot.user or message.content.startswith('!')
                
                try:
                    deleted_messages = await ctx.channel.purge(limit=limit, check=is_bot_or_command)
                    deleted = len(deleted_messages)
                    debug_logger.info("Bulk deleted %d messages", deleted)
                except discord.errors.Forbidden:
                    debug_logger.error("Forbidden error during bulk delete")
                    await status_msg.edit(content="⚠️ I don't have permission to bulk delete messages.")
                    return
                except discord.errors.NotFound:
                    # This can happen if a message was already deleted
                    debug_logger.warning("NotFound error during bulk delete")
                    await status_msg.edit(content="⚠️ Some messages could not be found. They may have been deleted already.")
                    # Continue with what we can delete
                    pass
                except Exception as e:
                    debug_logger.error("Error during bulk delete: %s", str(e))
                    await status_msg.edit(content=f"⚠️ Error during bulk delete: {str(e)}")
                    # Fall back to individual deletion
                    use_bulk_delete = False
            
            if not use_bulk_delete:
                # Individual deletion (works on older messages but is slower)
                debug_logger.debug("Using individual message deletion")
                async for message in ctx.channel.history(limit=limit):
                    # Delete if message is from the bot or starts with command prefix
                    if message.author == self.bot.user or message.content.startswith('!'):
                        try:
                            debug_logger.debug("Deleting message: %s", message.id)
                            await message.delete()
                            deleted += 1
                            # Add a longer delay to avoid rate limits
                            await asyncio.sleep(1.2)
                        except discord.errors.NotFound:
                            # Message already deleted, continue with others
                            debug_logger.warning("Message %s not found, may have been deleted already", message.id)
                            pass
                        except discord.errors.Forbidden:
                            debug_logger.error("Forbidden error during individual delete")
                            await status_msg.edit(content="⚠️ I don't have permission to delete some messages.")
                            break
                        except Exception as e:
                            # Log other errors but continue
                            debug_logger.error("Error deleting message %s: %s", message.id, str(e))
                            continue
            
            # Update status message with results or send a new one if the original was deleted
            debug_logger.info("Clean command completed, deleted %d messages", deleted)
            try:
                try:
                    # Try to edit the original status message
                    await status_msg.edit(content=f"✅ Cleaned {deleted} messages!")
                    
                    # Delete status message after 5 seconds
                    await asyncio.sleep(5)
                    try:
                        await status_msg.delete()
                    except discord.errors.NotFound:
                        debug_logger.info("Status message already deleted")
                    except Exception as e:
                        debug_logger.error("Error deleting status message: %s", str(e))
                except discord.errors.NotFound:
                    # If the original status message was deleted during cleanup, send a new one
                    debug_logger.info("Status message was deleted during cleanup, sending a new one")
                    new_status = await ctx.send(f"✅ Cleaned {deleted} messages!")
                    
                    # Delete new status message after 5 seconds
                    await asyncio.sleep(5)
                    try:
                        await new_status.delete()
                    except Exception as e:
                        debug_logger.error("Error deleting new status message: %s", str(e))
                except Exception as e:
                    debug_logger.error("Error updating original status message: %s", str(e))
                    # Try to send a new message as a fallback
                    await ctx.send(f"✅ Cleaned {deleted} messages!")
            except Exception as e:
                debug_logger.error("Error handling status messages: %s", str(e))
                
        except Exception as e:
            debug_logger.error("Unexpected error in clean command: %s", str(e))
            debug_logger.error("Traceback: %s", traceback.format_exc())
            try:
                await ctx.send(f"An error occurred: {str(e)}")
            except:
                pass
        
        deleted = 0
        
        # Determine if we should use bulk delete
        use_bulk_delete = use_bulk.lower() == "yes"
        if use_bulk.lower() == "auto":
            # In auto mode, we'll use bulk delete if available
            use_bulk_delete = hasattr(ctx.channel, "purge")
        
        if use_bulk_delete:
            # Use bulk delete (more efficient, but only works on messages less than 14 days old)
            def is_bot_or_command(message):
                return message.author == self.bot.user or message.content.startswith('!')
            
            try:
                deleted_messages = await ctx.channel.purge(limit=limit, check=is_bot_or_command)
                deleted = len(deleted_messages)
            except discord.errors.Forbidden:
                await status_msg.edit(content="⚠️ I don't have permission to bulk delete messages.")
                return
            except discord.errors.NotFound:
                # This can happen if a message was already deleted
                await status_msg.edit(content="⚠️ Some messages could not be found. They may have been deleted already.")
                # Continue with what we can delete
                pass
            except Exception as e:
                await status_msg.edit(content=f"⚠️ Error during bulk delete: {str(e)}")
                # Fall back to individual deletion
                use_bulk_delete = False
        
        if not use_bulk_delete:
            # Individual deletion (works on older messages but is slower)
            async for message in ctx.channel.history(limit=limit):
                # Delete if message is from the bot or starts with command prefix
                if message.author == self.bot.user or message.content.startswith('!'):
                    try:
                        await message.delete()
                        deleted += 1
                        # Add a longer delay to avoid rate limits
                        await asyncio.sleep(1.2)
                    except discord.errors.NotFound:
                        # Message already deleted, continue with others
                        pass
                    except discord.errors.Forbidden:
                        await status_msg.edit(content="⚠️ I don't have permission to delete some messages.")
                        break
                    except Exception as e:
                        # Log other errors but continue
                        print(f"Error deleting message: {str(e)}")
                        continue
        
        # Update status message with results
        await status_msg.edit(content=f"✅ Cleaned {deleted} messages!")
        
        # Delete status message after 5 seconds
        await asyncio.sleep(5)
        try:
            await status_msg.delete()
        except:
            pass

async def setup(bot):
    await bot.add_cog(Cleaner(bot))