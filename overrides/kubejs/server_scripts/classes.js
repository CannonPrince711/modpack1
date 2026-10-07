const CLASS_STATS = {
  warrior: {
    health: 6,
    armor: 3,
    damage: 2,
    speed: -0.01,
    spellPower: 0,
    spellEnginePower: 0
  },
  mage: {
    health: -2,
    armor: 0,
    damage: 0,
    speed: 0.01,
    spellPower: 0.15,
    spellEnginePower: 15
  },
  ranger: {
    health: 0,
    armor: 1,
    damage: 1,
    speed: 0.025,
    spellPower: 0,
    spellEnginePower: 0
  }
}

const CLASS_ATTRIBUTES = {
  health: "minecraft:generic.max_health",
  armor: "minecraft:generic.armor",
  damage: "minecraft:generic.attack_damage",
  speed: "minecraft:generic.movement_speed",
  spellPower: "irons_spellbooks:spell_power",
  // Spell Engine / RPG Series (Wizards, Paladins & Priests): a percentage that starts at 100, so +15 is the same +15%
  spellEnginePower: "spell_power:generic"
}

const AttributeRegistry = Java.loadClass("net.minecraftforge.registries.ForgeRegistries").ATTRIBUTES
const ResourceLocation = Java.loadClass("net.minecraft.resources.ResourceLocation")
const AttributeModifier = Java.loadClass("net.minecraft.world.entity.ai.attributes.AttributeModifier")

const CLASS_CURIOS_SLOTS = {
  warrior: ["ring", "belt", "hands"],
  mage: ["ring", "necklace", "charm", "spellbook"],
  ranger: ["ring", "belt", "back", "charm"]
}

// Utility items every class may carry; they live in class-restricted slots (backpacks use the Curios back slot).
const CURIOS_EXEMPT_NAMESPACES = ["sophisticatedbackpacks"]

// Spell Engine (the RPG Series: Paladins & Priests, Rogues & Warriors, Wizards, Archers) keeps its books, scrolls,
// trinkets and quivers in these Curios slots. The gear itself is class-specific, so every class may use the slots.
const SHARED_CURIOS_SLOTS = ["spell_book", "spell_scroll", "spell_trinket", "spell_quiver"]

const CuriosApi = Java.loadClass("top.theillusivec4.curios.api.CuriosApi")

function setModifier(player, stat, amount) {
  const attribute = AttributeRegistry.getValue(ResourceLocation.tryParse(CLASS_ATTRIBUTES[stat]))
  if (!attribute) throw new Error(`Missing class attribute: ${CLASS_ATTRIBUTES[stat]}`)

  const id = `dungeon_delvers.class.${stat}`
  player.removeAttribute(attribute, id)
  if (amount !== 0) {
    player.modifyAttribute(attribute, id, amount, AttributeModifier.Operation.ADDITION)
  }
}

function applyClass(player, className, level) {
  const stats = CLASS_STATS[className]
  if (!stats) return

  setModifier(player, "health", stats.health + (level - 1) * 0.5)
  setModifier(player, "armor", stats.armor)
  setModifier(player, "damage", stats.damage + (level - 1) * 0.15)
  setModifier(player, "speed", stats.speed)
  setModifier(player, "spellPower", stats.spellPower)
  setModifier(player, "spellEnginePower", stats.spellEnginePower)
}

function enforceCuriosSlots(player, className) {
  const inventoryOptional = CuriosApi.getCuriosInventory(player)
  if (!inventoryOptional.isPresent()) return

  const allowed = CLASS_CURIOS_SLOTS[className]
  const curios = inventoryOptional.get().getCurios().entrySet().iterator()
  while (curios.hasNext()) {
    const entry = curios.next()
    const slotName = String(entry.getKey())
    if (allowed.indexOf(slotName) >= 0 || SHARED_CURIOS_SLOTS.indexOf(slotName) >= 0) continue

    const stacks = entry.getValue().getStacks()
    for (let slot = 0; slot < stacks.getSlots(); slot++) {
      const equipped = stacks.getStackInSlot(slot)
      if (equipped.isEmpty()) continue
      if (CURIOS_EXEMPT_NAMESPACES.indexOf(String(equipped.id).split(":")[0]) >= 0) continue

      const returned = equipped.copy()
      stacks.setStackInSlot(slot, Item.of("minecraft:air"))
      player.give(returned)
      player.tell(`Your ${className} class cannot use the Curios ${slotName} slot.`)
    }
  }
}

PlayerEvents.chat(event => {
  const match = /^!class\s+(warrior|mage|ranger)$/i.exec(event.message.trim())
  if (!match) return

  event.cancel()
  const player = event.player
  const className = match[1].toLowerCase()
  const data = player.persistentData
  data.putString("ddo_class", className)
  data.putInt("ddo_applied_level", 0)
  player.tell(`Class selected: ${className}.`)
})

PlayerEvents.loggedIn(event => {
  event.player.persistentData.putInt("ddo_applied_level", 0)
})

PlayerEvents.tick(event => {
  const player = event.player
  if (player.level.isClientSide()) return

  const data = player.persistentData
  const className = data.getString("ddo_class")
  if (!CLASS_STATS[className]) return

  const curiosTick = data.getInt("ddo_curios_tick") + 1
  data.putInt("ddo_curios_tick", curiosTick % 20)
  if (curiosTick >= 20) enforceCuriosSlots(player, className)

  const xp = data.getInt("ddo_boss_xp")
  const level = Math.min(20, 1 + Math.floor(Math.sqrt(xp / 40)))
  if (data.getInt("ddo_applied_level") === level) return

  applyClass(player, className, level)
  data.putInt("ddo_applied_level", level)
  player.tell(`Delver level ${level} (${xp} boss XP).`)
})
