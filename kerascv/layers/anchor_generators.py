import tensorflow as tf


class AnchorGenerator(tf.keras.layers.Layer):
    def __init__(
        self,
        image_size,
        scales,
        aspect_ratios,
        anchor_stride=None,
        anchor_offset=None,
        clip_boxes=True,
        norm_coord=True,
        name=None,
        **kwargs
    ):
        """Constructs a AnchorGenerator."""

        self.image_size = image_size
        self.image_height = image_size[0]
        self.image_width = image_size[1]
        self.scales = scales
        self.aspect_ratios = aspect_ratios
        self.anchor_stride = anchor_stride
        self.anchor_offset = anchor_offset
        self.clip_boxes = clip_boxes
        self.norm_coord = norm_coord
        super(AnchorGenerator, self).__init__(name=name, **kwargs)

    def call(self, feature_map_size):
        feature_map_height = tf.cast(feature_map_size[0], dtype=tf.float32)
        feature_map_width = tf.cast(feature_map_size[1], dtype=tf.float32)
        image_height = tf.cast(self.image_height, dtype=tf.float32)
        image_width = tf.cast(self.image_width, dtype=tf.float32)

        min_image_size = tf.minimum(image_width, image_height)

        if self.anchor_stride is None:
            anchor_stride_height = tf.cast(
                min_image_size / feature_map_height, dtype=tf.float32
            )
            anchor_stride_width = tf.cast(
                min_image_size / feature_map_width, dtype=tf.float32
            )
        else:
            anchor_stride_height = tf.cast(self.anchor_stride[0], dtype=tf.float32)
            anchor_stride_width = tf.cast(self.anchor_stride[1], dtype=tf.float32)

        if self.anchor_offset is None:
            anchor_offset_height = tf.constant(0.5, dtype=tf.float32)
            anchor_offset_width = tf.constant(0.5, dtype=tf.float32)
        else:
            anchor_offset_height = tf.cast(self.anchor_offset[0], dtype=tf.float32)
            anchor_offset_width = tf.cast(self.anchor_offset[1], dtype=tf.float32)

        K = len(self.aspect_ratios)
        aspect_ratios_sqrt = tf.cast(tf.sqrt(self.aspect_ratios), tf.float32)
        scales = tf.cast(self.scales, dtype=tf.float32)
        # [1, 1, K]
        anchor_heights = tf.reshape(
            (scales / aspect_ratios_sqrt) * min_image_size, (1, 1, -1)
        )
        anchor_widths = tf.reshape(
            (scales * aspect_ratios_sqrt) * min_image_size, (1, 1, -1)
        )

        # [W]
        cx = (tf.range(feature_map_width) + anchor_offset_width) * anchor_stride_width
        # [H]
        cy = (
            tf.range(feature_map_height) + anchor_offset_height
        ) * anchor_stride_height
        # [H, W]
        cx_grid, cy_grid = tf.meshgrid(cx, cy)
        # [H, W, 1]
        cx_grid = tf.expand_dims(cx_grid, axis=-1)
        cy_grid = tf.expand_dims(cy_grid, axis=-1)
        # [H, W, K]
        cx_grid = tf.tile(cx_grid, (1, 1, K))
        cy_grid = tf.tile(cy_grid, (1, 1, K))
        # [H, W, K]
        anchor_heights = tf.tile(
            anchor_heights, (feature_map_height, feature_map_width, 1)
        )
        anchor_widths = tf.tile(
            anchor_widths, (feature_map_height, feature_map_width, 1)
        )

        # [H, W, K, 2]
        box_centers = tf.stack([cy_grid, cx_grid], axis=3)
        # [H * W * K, 2]
        box_centers = tf.reshape(box_centers, [-1, 2])
        # [H, W, K, 2]
        box_sizes = tf.stack([anchor_heights, anchor_widths], axis=3)
        # [H * W * K, 2]
        box_sizes = tf.reshape(box_sizes, [-1, 2])
        # y_min, x_min, y_max, x_max
        # [H * W * K, 4]
        box_tensor = tf.concat(
            [box_centers - 0.5 * box_sizes, box_centers + 0.5 * box_sizes], axis=1
        )

        if self.clip_boxes:
            y_min, x_min, y_max, x_max = tf.split(
                box_tensor, num_or_size_splits=4, axis=1
            )
            y_min_clipped = tf.maximum(tf.minimum(y_min, self.image_height), 0)
            y_max_clipped = tf.maximum(tf.minimum(y_max, self.image_height), 0)
            x_min_clipped = tf.maximum(tf.minimum(x_min, self.image_width), 0)
            x_max_clipped = tf.maximum(tf.minimum(x_max, self.image_width), 0)
            box_tensor = tf.concat(
                [y_min_clipped, x_min_clipped, y_max_clipped, x_max_clipped], axis=1
            )

        if self.norm_coord:
            box_tensor = box_tensor / tf.constant(
                [
                    [
                        self.image_height,
                        self.image_width,
                        self.image_height,
                        self.image_width,
                    ]
                ],
                dtype=box_tensor.dtype,
            )

        return box_tensor

    def get_config(self):
        config = {
            "image_size": self.image_size,
            "scales": self.scales,
            "aspect_ratios": self.aspect_ratios,
            "anchor_stride": self.anchor_stride,
            "anchor_offset": self.anchor_offset,
            "clip_boxes": self.clip_boxes,
            "norm_coord": self.norm_coord,
        }
        base_config = super(AnchorGenerator, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))
