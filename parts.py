from maya import cmds
from int_rigging import chain

def hand(parent, side, fingers, phalanxes, template, color):
    hand_grp = cmds.createNode("transform", n="{0}_hand_grp".format(side))

    if parent:
        cmds.parent(hand_grp, parent)

    for finger in fingers:
        joints = []
        for i in range(phalanxes):
            jnt_name = "{0}_finger{1}0{2}_jnt".format(side, finger, i)
            if cmds.objExists(jnt_name):
                joints.append(jnt_name)
                
        chain.fkchain(hand_grp, joints, template, color)
        