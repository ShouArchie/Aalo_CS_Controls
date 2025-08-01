def onebyonesnake(acc: float = 0.1, vel: float = 0.1, blend_r: float = 0.001):
    # Cold Spray script that goes right up left up right up etc. 
    return f"""
def cold_spray():
    # First loop - 7 iterations with downward Z movement
    i = 0
    while i < 7:
        movel(pose_trans(get_actual_tcp_pose(), p[0, -0.0274, 0, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
        movel(pose_trans(get_actual_tcp_pose(), p[0, 0, -0.002, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
        movel(pose_trans(get_actual_tcp_pose(), p[0, 0.0274, 0, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
        if i < 6:
            movel(pose_trans(get_actual_tcp_pose(), p[0, 0, -0.002, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
        end
        i = i + 1
    end
    
    # Second loop - 7 iterations with upward Z movement
    i = 0
    while i < 7:
        movel(pose_trans(get_actual_tcp_pose(), p[0, -0.0274, 0, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
        movel(pose_trans(get_actual_tcp_pose(), p[0, 0, 0.002, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
        
        if i < 6:
            movel(pose_trans(get_actual_tcp_pose(), p[0, 0.0274, 0, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
            movel(pose_trans(get_actual_tcp_pose(), p[0, 0, 0.002, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
        end
        i = i + 1
    end
    
    # Final extra left movement
    movel(pose_trans(get_actual_tcp_pose(), p[0, -0.0274, 0, 0, 0, 0]), a={acc}, v={vel}, r={blend_r})
end

cold_spray()
"""
