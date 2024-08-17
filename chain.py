from maya import cmds
from maya import OpenMaya as om

def fkchain(parent, joints, template, color, settings_shape):
    controls = []
    joint_parent = parent

    # joints = cmds.ls(sl=True)
    # will print out the names of all joints selected in the outliner
        
    for jnt in joints:
        
        # create a control and a group for each joint and rename group and control
        grp, ctl = create_control_from_template(jnt.replace("jnt", "ctl"), joint_parent, template, color, settings_shape)
            
        # position the control on the joint
        #cmds.matchTransform(ctl, jnt) 
        cmds.delete(cmds.parentConstraint(jnt, grp, mo=False))
        
        joint_parent = ctl  # update value of joint_parent to 'ctl' 
        controls.append(ctl)
            
        # drive the joint
        cmds.pointConstraint(ctl, jnt)
        cmds.orientConstraint(ctl, jnt)
        cmds.scaleConstraint(ctl, jnt)

    return controls

    for side in ["lf", "rt"]:
        for phalanx in ["A", "B", "C", "D", "E"]:
            joints = []
            for i in range(4):
                jnt_name = "{0}_finger{1}0{2}_jnt".format(side, phalanx, i)
                if cmds.objExists(jnt_name):
                    joints.append(jnt_name)

def create_control_from_template(name, parent, template, color, settings_node):
    # create a control and a group for each joint and rename group and control
    grp, ctl = cmds.duplicate(template, n=name.replace("ctl", "grp"), rc=True)
    # rc = rename children
    ctl = cmds.rename(ctl, name)

    # parent group under the previous control
    if parent:    # if joint_parent has a value, execute next line
        cmds.parent(grp, parent)

    if settings_node:
        cmds.parent(settings_node, ctl, s=True, r=True, add=True)
    
    cmds.setAttr("{0}.overrideEnabled".format(ctl), 1)
    cmds.setAttr("{0}.overrideColor".format(ctl), color)

    return grp, ctl

def place_pole_vector(polevector, jointA, jointB, jointC):
    #posA = cmds.xform("lf_arm00_jnt", q=True, t=True, ws=True)
    OA = om.MVector(*cmds.xform(jointA, q=True, t=True, ws=True))
    OB = om.MVector(*cmds.xform(jointB, q=True, t=True, ws=True))
    OC = om.MVector(*cmds.xform(jointC, q=True, t=True, ws=True))

    AC = OC - OA
    AB = OB - OA
    BC = OC - OB

    multiplier = (AC*AB)/(AC*AC)
    projection = AC * multiplier + OA
    direction = (OB - projection).normal()

    length = AB.length() + BC.length()
    pv_pos = OB + direction*length

    cmds.xform(polevector, t=[pv_pos.x, pv_pos.y, pv_pos.z], ws=True)

def ikchain(name, side, parent, joints, iktemplate, pvtemplate, color, settings_node=None, stretch_direction="x"):
    squash_directions = ["x", "y", "z"]
    squash_directions.remove(stretch_direction)

    ikgrp, ikctl = create_control_from_template("{0}_{1}ik_ctl".format(side, name), parent, iktemplate, color, settings_node)
    pvgrp, pvctl = create_control_from_template("{0}_{1}pv_ctl".format(side, name), parent, pvtemplate, color, settings_node)

    cmds.delete(cmds.parentConstraint(joints[-1], ikgrp, mo=False))

    handle, effector = cmds.ikHandle(sj=joints[0], ee=joints[-1], sol="ikRPsolver")  
    cmds.parent(handle, ikctl)

    place_pole_vector(pvgrp, *joints)
    cmds.poleVectorConstraint(pvctl, handle)

    if settings_node:
        cmds.addAttr(settings_node, at="double", ln="autoStretch", min=0, max=1, dv=0, k=True)
        cmds.addAttr(settings_node, at="double", ln="autoSquash", min=0, max=1, dv=0, k=True)
        cmds.addAttr(settings_node, at="double", ln="upperLength", dv=1, k=True)
        cmds.addAttr(settings_node, at="double", ln="lowerLength", dv=1, k=True)
        cmds.addAttr(settings_node, at="double", ln="pinToPv", min=0, max=1, dv=0, k=True)

    # stretch setup
    loc = cmds.spaceLocator(n="{0}_{1}distance_loc".format(side, name))[0]
    if parent:
        cmds.parent(loc, parent)
    
    cmds.delete(cmds.parentConstraint(joints[0], loc, mo=False))

    dbt = cmds.createNode("distanceBetween", n="{0}_{1}_dbt".format(side, name))
    cmds.connectAttr("{0}.worldMatrix[0]".format(loc), "{0}.inMatrix1".format(dbt))
    cmds.connectAttr("{0}.worldMatrix[0]".format(ikctl), "{0}.inMatrix2".format(dbt))

    stretch_factor_mdn = cmds.createNode("multiplyDivide", n="{0}_{1}stretchFactor_mdn".format(side, name))
    cmds.connectAttr("{0}.distance".format(dbt), "{0}.input1X".format(stretch_factor_mdn))
    input2x_value = cmds.getAttr("{0}.t{1}".format(joints[1], stretch_direction)) + cmds.getAttr("{0}.tx".format(joints[2]))
    cmds.setAttr("{0}.input2X".format(stretch_factor_mdn), abs(input2x_value))  ## ADDED ABS HERE
    cmds.setAttr("{0}.operation".format(stretch_factor_mdn), 2)

    # !!! don't create a connection between the outputX of the stretch_factor and tx of lf_arm01_jnt because it's addressed with blend colors

    stretch_clamp = cmds.createNode("clamp", n="{0}_{1}StretchFactor_clm".format(side, name))
    cmds.connectAttr("{0}.outputX".format(stretch_factor_mdn), "{0}.inputR".format(stretch_clamp))
    cmds.setAttr("{0}.minR".format(stretch_clamp), 1)
    cmds.setAttr("{0}.maxR".format(stretch_clamp), 999999)
    
    stretch_blend_colors = []
    for jnt in joints[1:]:
        jnt_stretch_mdn = cmds.createNode("multiplyDivide", n=jnt.replace("_jnt", "stretchFactor_mdn"))
        cmds.connectAttr("{0}.outputR".format(stretch_clamp), "{0}.input2X".format(jnt_stretch_mdn))  # .tx instead of input2X?
        input1x_value = cmds.getAttr("{0}.t{1}".format(jnt, stretch_direction))
        cmds.setAttr("{0}.input1X".format(jnt_stretch_mdn), input1x_value)

        jnt_stretch_blc = cmds.createNode("blendColors", n=jnt.replace("_jnt", "stretchFactor_blc"))
        cmds.setAttr("{0}.color2R".format(jnt_stretch_blc), input1x_value)
        cmds.connectAttr("{0}.outputX".format(jnt_stretch_mdn), "{0}.color1R".format(jnt_stretch_blc))
        cmds.connectAttr("{0}.autoStretch".format(settings_node), "{0}.blender".format(jnt_stretch_blc))

        stretch_blend_colors.append(jnt_stretch_blc)
        # delete after creating upper/lower mdn to avoid error
        # cmds.connectAttr("{0}.outputR".format(jnt_stretch_blc), "{0}.tx".format(jnt))  # 'lf_arm01_jnt.translateX' already has an incoming connection from 'lf_arm01_jnt2.outputR'

    # squash setup
    squash_factor_mdn = cmds.createNode("multiplyDivide", n="{0}_{1}squashFactor_mdn".format(side, name))
    cmds.connectAttr("{0}.distance".format(dbt), "{0}.input2X".format(squash_factor_mdn))
    input2x_value = cmds.getAttr("{0}.t{1}".format(joints[1], stretch_direction)) + cmds.getAttr("{0}.tx".format(joints[2]))
    cmds.setAttr("{0}.input1X".format(squash_factor_mdn), abs(input2x_value))  ## ADDED ABS HERE
    cmds.setAttr("{0}.operation".format(squash_factor_mdn), 2)

    squash_clamp = cmds.createNode("clamp", n="{0}_{1}squashFactor_clm".format(side, name))
    cmds.connectAttr("{0}.outputX".format(squash_factor_mdn), "{0}.inputR".format(squash_clamp))
    cmds.setAttr("{0}.minR".format(squash_clamp), 0)
    cmds.setAttr("{0}.maxR".format(squash_clamp), 1)
    
    for jnt in joints[:-1]:
        jnt_squash_blc = cmds.createNode("blendColors", n=jnt.replace("_jnt", "squashFactor_blc"))
        cmds.setAttr("{0}.color2R".format(jnt_squash_blc), 1)
        cmds.connectAttr("{0}.outputR".format(squash_clamp), "{0}.color1R".format(jnt_squash_blc))
        cmds.connectAttr("{0}.autoSquash".format(settings_node), "{0}.blender".format(jnt_squash_blc))

        cmds.connectAttr("{0}.outputR".format(jnt_squash_blc), "{0}.s{1}".format(jnt, squash_directions[0]))
        cmds.connectAttr("{0}.outputR".format(jnt_squash_blc), "{0}.s{1}".format(jnt, squash_directions[1]))

    # upper arm length
    upper_arm_mdn = cmds.createNode("multiplyDivide", n="{0}_{1}upperLength_mdn".format(side, name))
    cmds.connectAttr("{0}.outputR".format(stretch_blend_colors[0]), "{0}.input1X".format(upper_arm_mdn))
    cmds.connectAttr("{0}.upperLength".format(settings_node), "{0}.input2X".format(upper_arm_mdn))

    # lower arm length
    lower_arm_mdn = cmds.createNode("multiplyDivide", n="{0}_{1}lowerLength_mdn".format(side, name))
    cmds.connectAttr("{0}.outputR".format(stretch_blend_colors[1]), "{0}.input1X".format(lower_arm_mdn))
    cmds.connectAttr("{0}.lowerLength".format(settings_node), "{0}.input2X".format(lower_arm_mdn))

    # pin to pole vector
    upper_pv_dbt = cmds.createNode("distanceBetween", n="{0}_{1}upperPinPv_dbt".format(side, name))
    cmds.connectAttr("{0}.worldMatrix[0]".format(loc), "{0}.inMatrix1".format(upper_pv_dbt))
    cmds.connectAttr("{0}.worldMatrix[0]".format(pvctl), "{0}.inMatrix2".format(upper_pv_dbt))

    jnt1_pinpv_blc = cmds.createNode("blendColors", n="{0}_{1}upperPinPv_blc".format(side, name))
    cmds.connectAttr("{0}.outputX".format(upper_arm_mdn), "{0}.color2R".format(jnt1_pinpv_blc))
    cmds.connectAttr("{0}.distance".format(upper_pv_dbt), "{0}.color1R".format(jnt1_pinpv_blc))
    cmds.connectAttr("{0}.pinToPv".format(settings_node), "{0}.blender".format(jnt1_pinpv_blc))
    cmds.connectAttr("{0}.outputR".format(jnt1_pinpv_blc), "{0}.t{1}".format(joints[1], stretch_direction))

    lower_pv_dbt = cmds.createNode("distanceBetween", n="{0}_{1}lowerPinPv_dbt".format(side, name))
    cmds.connectAttr("{0}.worldMatrix[0]".format(ikctl), "{0}.inMatrix1".format(lower_pv_dbt))
    cmds.connectAttr("{0}.worldMatrix[0]".format(pvctl), "{0}.inMatrix2".format(lower_pv_dbt))

    jnt2_pinpv_blc = cmds.createNode("blendColors", n="{0}_{1}lowerPinPv_blc".format(side, name))
    cmds.connectAttr("{0}.outputX".format(lower_arm_mdn), "{0}.color2R".format(jnt2_pinpv_blc))
    cmds.connectAttr("{0}.distance".format(lower_pv_dbt), "{0}.color1R".format(jnt2_pinpv_blc))
    cmds.connectAttr("{0}.pinToPv".format(settings_node), "{0}.blender".format(jnt2_pinpv_blc))
    cmds.connectAttr("{0}.outputR".format(jnt2_pinpv_blc), "{0}.t{1}".format(joints[2], stretch_direction))

    return ikctl, pvctl

def ikfkchain(name, side, parent, joints, fktemplate, iktemplate, pvtemplate, fkcolor, ikcolor, stretch_direction="x"):
    rig_group = cmds.createNode("transform", n="{0}_{1}_grp".format(side, name))
    if parent:
        cmds.parent(rig_group, parent)
    
    # Settings shape
    settings_loc = cmds.spaceLocator(n="{0}_{1}settings_loc".format(side, name))
    cmds.parent(settings_loc, rig_group)
    settings_shape = cmds.listRelatives(settings_loc, c=True, s=True)[0]
    cmds.addAttr(settings_shape, at="double", ln="ik", min=0, max=1, dv=0, k=True)
    
    # duplicate chains - one for IK, one for FK
    ik_drivers_grp = cmds.createNode("transform", n="{0}_{1}ikRig_grp".format(side, name))
    cmds.parent(ik_drivers_grp, rig_group)

    fk_joints = duplicate_chain(joints, rig_group, "_jnt", "fk_jnt")
    ik_driver_joints = duplicate_chain(joints, ik_drivers_grp, "_jnt", "ikDriver_jnt")
    ik_joints = duplicate_chain(joints, rig_group, "_jnt", "ik_jnt")
    blend_joints = duplicate_chain(joints, rig_group, "_jnt", "blend_jnt")

    # connect blend chains
    for fkjnt, ikjnt, bjnt in zip(fk_joints, ik_joints, blend_joints):
        for transformation in ["translate", "rotate", "scale"]:
            blc = cmds.createNode("blendColors", n=bjnt.replace("_jnt", "{0}_jnt".format(transformation.capitalize())))
            cmds.connectAttr("{0}.{1}".format(ikjnt, transformation), "{0}.color1".format(blc))
            cmds.connectAttr("{0}.{1}".format(fkjnt, transformation), "{0}.color2".format(blc))
            cmds.connectAttr("{0}.ik".format(settings_shape), "{0}.blender".format(blc))
            cmds.connectAttr("{0}.output".format(blc), "{0}.{1}".format(bjnt,transformation))

    for ikdjnt, ikjnt in zip(ik_driver_joints, ik_joints):
        cmds.pointConstraint(ikdjnt, ikjnt)
        cmds.orientConstraint(ikdjnt, ikjnt)
        cmds.scaleConstraint(ikdjnt, ikjnt)

    for bjnt, jnt in zip(blend_joints, joints):
        cmds.pointConstraint(bjnt, jnt)
        cmds.orientConstraint(bjnt, jnt)
        cmds.connectAttr("{0}.scale".format(bjnt), "{0}.scale".format(jnt))
    
    # rigging the arm
    fkcontrols = fkchain(rig_group, fk_joints, fktemplate, fkcolor, settings_shape)
    ikctl, pvctl = ikchain(name, side, rig_group, ik_driver_joints, iktemplate, pvtemplate, ikcolor, settings_shape, stretch_direction)

    # control visibility
    rvr = cmds.createNode("reverse", n="{0}_{1}fkIk_rvr".format(side, name))
    cmds.connectAttr("{0}.ik".format(settings_shape), "{0}.inputX".format(rvr))

    for ctl in [ikctl, pvctl]:
        grp = cmds.listRelatives(ctl, p=True)[0]
        cmds.connectAttr("{0}.ik".format(settings_shape), "{0}.v".format(grp))

    grp = cmds.listRelatives(fkcontrols[0], p=True)[0]
    cmds.connectAttr("{0}.outputX".format(rvr), "{0}.v".format(grp))

def duplicate_chain(joints, parent, replace_what, replace_with):
    new_joints = []
    new_joints_parent = parent

    for jnt in joints:
        new_jnt = cmds.duplicate(jnt, n=jnt.replace(replace_what, replace_with), po=True)[0]

        if new_joints_parent:
            cmds.parent(new_jnt, new_joints_parent)
        
        new_joints_parent = new_jnt
        new_joints.append(new_jnt)

    return new_joints