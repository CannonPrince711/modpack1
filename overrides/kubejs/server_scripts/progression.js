// Boss currency: Lightman's Currency coins, spent at the Odyssey Quartermaster (shop.js).
// Overworld bosses pay gold coins, Nether bosses emerald coins, End bosses more emerald coins.
const COINS_OVERWORLD = ["lightmanscurrency:coin_gold", 5]
const COINS_NETHER = ["lightmanscurrency:coin_emerald", 3]
const COINS_END = ["lightmanscurrency:coin_emerald", 8]

const BOSS_REWARDS = {
  "cataclysm:ancient_remnant": {
    coins: COINS_OVERWORLD,
    xp: 50,
    item: "minecraft:ancient_debris",
    name: "Relic of the Sunken Pharaoh"
  },
  "cataclysm:netherite_monstrosity": {
    coins: COINS_NETHER,
    xp: 75,
    item: "minecraft:blaze_powder",
    name: "Monstrosity Ember"
  },
  "cataclysm:ender_guardian": {
    coins: COINS_END,
    xp: 100,
    item: "minecraft:echo_shard",
    name: "Guardian's Void Sigil"
  }
}

// Other single-phase bosses in the pack pay coins only (no campaign XP or trophy).
const COIN_ONLY_BOSSES = {
  "mowziesmobs:ferrous_wroughtnaut": COINS_OVERWORLD,
  "mowziesmobs:frostmaw": COINS_OVERWORLD,
  "mowziesmobs:umvuthi": COINS_OVERWORLD,
  "mowziesmobs:sculptor": COINS_OVERWORLD,
  "bosses_of_mass_destruction:lich": COINS_OVERWORLD,
  "bosses_of_mass_destruction:void_blossom": COINS_OVERWORLD,
  "bosses_of_mass_destruction:gauntlet": COINS_OVERWORLD,
  "cataclysm:wadjet": COINS_OVERWORLD,
  "cataclysm:ignis": COINS_NETHER,
  "cataclysm:the_harbinger": COINS_NETHER,
  "cataclysm:the_leviathan": COINS_NETHER,
  "cataclysm:scylla": COINS_NETHER,
  "cataclysm:maledictus": COINS_NETHER,
  "soulsweapons:accursed_lord_boss": COINS_NETHER,
  "soulsweapons:chaos_monarch": COINS_NETHER,
  "soulsweapons:draugr_boss": COINS_NETHER,
  "soulsweapons:remnant": COINS_NETHER,
  "bosses_of_mass_destruction:obsidilith": COINS_END
}

EntityEvents.death(event => {
  const reward = BOSS_REWARDS[event.entity.type]
  const coins = reward ? reward.coins : COIN_ONLY_BOSSES[event.entity.type]
  if (!coins) return

  const participants = event.server.getPlayerList().getPlayers()
  for (let index = 0; index < participants.size(); index++) {
    const player = participants.get(index)
    if (String(player.level.dimension) !== String(event.entity.level.dimension)) continue
    if (player.distanceTo(event.entity) > 64) continue

    player.give(Item.of(coins[0], coins[1]))
    player.tell(`Boss bounty: ${coins[1]} ${String(coins[0]).split(":")[1].replace("coin_", "")} coins.`)
    if (!reward) continue

    const data = player.persistentData
    const oldXp = data.getInt("ddo_boss_xp")
    data.putInt("ddo_boss_xp", oldXp + reward.xp)
    data.putInt("ddo_applied_level", 0)
    player.give(
      Item.of(reward.item, {
        display: {
          Name: JSON.stringify({ text: reward.name, italic: false, color: "gold" }),
          Lore: [JSON.stringify({ text: "A trophy of the Odyssey.", italic: false, color: "gray" })]
        }
      })
    )
    player.tell(`${reward.name}: +${reward.xp} boss XP.`)
  }
})
