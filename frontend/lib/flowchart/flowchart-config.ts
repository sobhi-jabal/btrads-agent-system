import { Node, Edge, MarkerType } from 'reactflow'

// Define BT-RADS flowchart nodes
export const getBTRADSNodes = (): Node[] => [
  {
    id: 'start',
    type: 'btradsNode',
    position: { x: 400, y: 0 },
    data: {
      label: 'Brain Tumor Follow-up',
      type: 'data-extraction',
      status: 'pending'
    }
  },
  {
    id: 'node_1_suitable_prior',
    type: 'btradsNode',
    position: { x: 400, y: 100 },
    data: {
      label: 'Suitable Prior?',
      type: 'decision',
      status: 'pending'
    }
  },
  {
    id: 'outcome_bt_0',
    type: 'btradsNode',
    position: { x: 600, y: 200 },
    data: {
      label: 'BT-0 (Baseline)',
      type: 'outcome',
      status: 'pending',
      btradsScore: '0'
    }
  },
  {
    id: 'node_2_imaging_assessment',
    type: 'btradsNode',
    position: { x: 400, y: 200 },
    data: {
      label: 'Imaging Assessment',
      type: 'decision',
      status: 'pending'
    }
  },
  {
    id: 'outcome_bt_2',
    type: 'btradsNode',
    position: { x: 400, y: 300 },
    data: {
      label: 'BT-2 (Stable)',
      type: 'outcome',
      status: 'pending',
      btradsScore: '2'
    }
  },
  {
    id: 'node_3a_medications',
    type: 'btradsNode',
    position: { x: 200, y: 300 },
    data: {
      label: 'On Medications?',
      type: 'decision',
      status: 'pending'
    }
  },
  {
    id: 'node_3b_avastin_response',
    type: 'btradsNode',
    position: { x: 100, y: 400 },
    data: {
      label: 'Avastin Response',
      type: 'decision',
      status: 'pending'
    }
  },
  {
    id: 'node_3c_steroid_effects',
    type: 'btradsNode',
    position: { x: 300, y: 400 },
    data: {
      label: 'Steroid Effects',
      type: 'decision',
      status: 'pending'
    }
  },
  {
    id: 'outcome_bt_1a',
    type: 'btradsNode',
    position: { x: 200, y: 500 },
    data: {
      label: 'BT-1a (Improved)',
      type: 'outcome',
      status: 'pending',
      btradsScore: '1a'
    }
  },
  {
    id: 'outcome_bt_1b',
    type: 'btradsNode',
    position: { x: 100, y: 500 },
    data: {
      label: 'BT-1b (Medication Effect)',
      type: 'outcome',
      status: 'pending',
      btradsScore: '1b'
    }
  },
  {
    id: 'node_4_time_since_xrt',
    type: 'btradsNode',
    position: { x: 600, y: 300 },
    data: {
      label: 'Time Since XRT',
      type: 'decision',
      status: 'pending'
    }
  },
  {
    id: 'outcome_bt_3a',
    type: 'btradsNode',
    position: { x: 500, y: 400 },
    data: {
      label: 'BT-3a (Favor Treatment)',
      type: 'outcome',
      status: 'pending',
      btradsScore: '3a'
    }
  },
  {
    id: 'node_5_what_is_worse',
    type: 'btradsNode',
    position: { x: 700, y: 400 },
    data: {
      label: 'What is Worse?',
      type: 'decision',
      status: 'pending'
    }
  },
  {
    id: 'outcome_bt_3b',
    type: 'btradsNode',
    position: { x: 600, y: 500 },
    data: {
      label: 'BT-3b (Indeterminate)',
      type: 'outcome',
      status: 'pending',
      btradsScore: '3b'
    }
  },
  {
    id: 'node_6_how_much_worse',
    type: 'btradsNode',
    position: { x: 800, y: 500 },
    data: {
      label: 'How Much Worse?',
      type: 'decision',
      status: 'pending'
    }
  },
  {
    id: 'outcome_bt_4',
    type: 'btradsNode',
    position: { x: 900, y: 600 },
    data: {
      label: 'BT-4 (Highly Suspicious)',
      type: 'outcome',
      status: 'pending',
      btradsScore: '4'
    }
  },
  {
    id: 'node_7_progressive',
    type: 'btradsNode',
    position: { x: 700, y: 600 },
    data: {
      label: 'Progressive?',
      type: 'decision',
      status: 'pending'
    }
  },
  {
    id: 'outcome_bt_3c',
    type: 'btradsNode',
    position: { x: 700, y: 700 },
    data: {
      label: 'BT-3c (Favor Tumor)',
      type: 'outcome',
      status: 'pending',
      btradsScore: '3c'
    }
  }
]

// Define BT-RADS flowchart edges
export const getBTRADSEdges = (): Edge[] => [
  {
    id: 'start-node1',
    source: 'start',
    target: 'node_1_suitable_prior',
    type: 'smoothstep'
  },
  {
    id: 'node1-bt0',
    source: 'node_1_suitable_prior',
    target: 'outcome_bt_0',
    label: 'No',
    type: 'smoothstep'
  },
  {
    id: 'node1-node2',
    source: 'node_1_suitable_prior',
    target: 'node_2_imaging_assessment',
    label: 'Yes',
    type: 'smoothstep'
  },
  {
    id: 'node2-bt2',
    source: 'node_2_imaging_assessment',
    target: 'outcome_bt_2',
    label: 'Unchanged',
    type: 'smoothstep'
  },
  {
    id: 'node2-node3a',
    source: 'node_2_imaging_assessment',
    target: 'node_3a_medications',
    label: 'Improved',
    type: 'smoothstep'
  },
  {
    id: 'node2-node4',
    source: 'node_2_imaging_assessment',
    target: 'node_4_time_since_xrt',
    label: 'Worse',
    type: 'smoothstep'
  },
  {
    id: 'node3a-node3b',
    source: 'node_3a_medications',
    target: 'node_3b_avastin_response',
    label: 'Avastin',
    type: 'smoothstep'
  },
  {
    id: 'node3a-node3c',
    source: 'node_3a_medications',
    target: 'node_3c_steroid_effects',
    label: 'Steroids',
    type: 'smoothstep'
  },
  {
    id: 'node3a-bt1a',
    source: 'node_3a_medications',
    target: 'outcome_bt_1a',
    label: 'Neither',
    type: 'smoothstep'
  },
  {
    id: 'node3b-bt1b',
    source: 'node_3b_avastin_response',
    target: 'outcome_bt_1b',
    label: 'First Study',
    type: 'smoothstep'
  },
  {
    id: 'node3b-bt1a',
    source: 'node_3b_avastin_response',
    target: 'outcome_bt_1a',
    label: 'Sustained',
    type: 'smoothstep'
  },
  {
    id: 'node3c-bt1b2',
    source: 'node_3c_steroid_effects',
    target: 'outcome_bt_1b',
    label: 'Likely',
    type: 'smoothstep'
  },
  {
    id: 'node3c-bt1a2',
    source: 'node_3c_steroid_effects',
    target: 'outcome_bt_1a',
    label: 'Unlikely',
    type: 'smoothstep'
  },
  {
    id: 'node4-bt3a',
    source: 'node_4_time_since_xrt',
    target: 'outcome_bt_3a',
    label: '< 90 days',
    type: 'smoothstep'
  },
  {
    id: 'node4-node5',
    source: 'node_4_time_since_xrt',
    target: 'node_5_what_is_worse',
    label: '≥ 90 days',
    type: 'smoothstep'
  },
  {
    id: 'node5-bt3b',
    source: 'node_5_what_is_worse',
    target: 'outcome_bt_3b',
    label: 'FLAIR or ENH',
    type: 'smoothstep'
  },
  {
    id: 'node5-node6',
    source: 'node_5_what_is_worse',
    target: 'node_6_how_much_worse',
    label: 'FLAIR and ENH',
    type: 'smoothstep'
  },
  {
    id: 'node6-bt4',
    source: 'node_6_how_much_worse',
    target: 'outcome_bt_4',
    label: '> 40%',
    type: 'smoothstep'
  },
  {
    id: 'node6-node7',
    source: 'node_6_how_much_worse',
    target: 'node_7_progressive',
    label: '< 40%',
    type: 'smoothstep'
  },
  {
    id: 'node7-bt4-2',
    source: 'node_7_progressive',
    target: 'outcome_bt_4',
    label: 'Yes',
    type: 'smoothstep'
  },
  {
    id: 'node7-bt3c',
    source: 'node_7_progressive',
    target: 'outcome_bt_3c',
    label: 'No',
    type: 'smoothstep'
  }
]