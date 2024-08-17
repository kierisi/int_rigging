from maya import cmds

def fkchain(parent, joints, template, color):
    joint_parent = parent

    # joints = cmds.ls(sl=True)
    # will print out the names of all joints selected in the outliner
        
    for jnt in joints:
        
        # create a control and a group for each joint and rename group and control
        grp, ctl = cmds.duplicate(template, n=jnt.replace("jnt", "grp"), rc=True)
        # rc = rename children
        ctl = cmds.rename(ctl, jnt.replace("jnt", "ctl"))
            
        # position the control on the joint
        #cmds.matchTransform(ctl, jnt) 
        cmds.delete(cmds.parentConstraint(jnt, grp, mo=False))
            
        # parent group under the previous control
        if joint_parent:    # if joint_parent has a value, execute next line
            cmds.parent(grp, joint_parent)
        
        joint_parent = ctl  # update value of joint_parent to 'ctl' 
            
        # drive the joint
        cmds.pointConstraint(ctl, jnt)
        cmds.orientConstraint(ctl, jnt)
        cmds.scaleConstraint(ctl, jnt)

        # Freeze transformations
        #cmds.makeIdentity(ctl, apply=True)
            
        # set color
        cmds.setAttr("{0}.overrideEnabled".format(ctl), 1)
        cmds.setAttr("{0}.overrideColor".format(ctl), color)

for side in ["lf", "rt"]:
    for phalanx in ["A", "B", "C", "D", "E"]:
        joints = []
        for i in range(4):
            jnt_name = "{0}_finger{1}0{2}_jnt".format(side, phalanx, i)
            if cmds.objExists(jnt_name):
                joints.append(jnt_name)