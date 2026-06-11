# The Stigmergy Cliff

*A note for the Formal Protocol Theory reading group, on Aswale, López, Ammartayakun & Pinciroli, "Hacking the Colony" (AAMAS 2022).*

The paper looks like it is about ants. It is about coordination protocols, and it contains a result I think protocol theory should take as a first-class object.

## The setup

Stigmergy is coordination stripped to its minimum. Agents write signals into a shared medium and read them back. There are no direct messages, no identities, no central authority. The trail is the protocol. This is not a toy. Gossip networks, reputation-by-environment, price signals in a market, mempool ordering: a large family of real coordination mechanisms are authentication-free shared-medium protocols, and stigmergy is their cleanest instance.

## The result

A small minority of agents depositing an **indistinguishable** forged signal collapses the whole protocol. In the paper, 3 percent of agents laying misleading pheromone cuts food collection roughly 150-fold. With forgery that never decays, 0.39 percent is enough.

The collapse is not bad luck and it is not a parameter you can tune away. It is structural. The read side cannot authenticate the medium, so honest agents amplify forged signals exactly as they amplify real ones. They build the trap together. Any authentication-free shared-medium protocol inherits this cliff. That is the claim worth generalizing past ants.

## The defence, and its price

The paper's countermeasure is a second-order signal: a cautionary pheromone that means "I followed this and found nothing, distrust it." It helps, sometimes a lot. It never fully restores the protocol, and it has a cost. Over-cautious agents abandon real trails too. The defence buys safety with liveness, and it has its own sweet spot: too little caution and the attack stands, too much and the colony distrusts everything and starves on its own.

So the honest picture is not "attack, then patched." It is a tradeoff surface. **Capture versus liveness** is the real object, and where a protocol sits on that surface, how sharp its cliff is, and what a defence costs to move it, are the properties we should be measuring.

## The systems reading

The cautionary layer is a reference signal correcting a homeostat. Conant and Ashby tell us every good regulator must model the system it regulates. Here the colony must model something more specific: that its own coordination medium can be corrupted. The defence is the system acquiring an internal model of its own attack surface. Resilience is not the colony modelling its environment better. It is the colony modelling the adversarial corruption of its own channel, and acting on that model. This is the governance lens applied to a protocol rather than to an organization.

## Why I built a bench, not a summary

The repository alongside this note is a small, tunable model where the protocol is factored into swappable read and write policies. You can dial the detractor fraction and the forgery's persistence and watch the cliff appear, then switch on the defence and watch liveness partly return. The point of building it is that capture-versus-liveness should be something you can *run*, and eventually something you can *prove bounds on*, not just assert.

That is where I want to take this. If protocols are systems in the formal sense the convergence work claims, then a coordination protocol's cliff should be a derivable property of its structure, and there should be a provable floor below which no second-order defence can hold. The open question I would put to the group: which trust-layer topologies move the cliff furthest for the least liveness cost, and is that floor real?
